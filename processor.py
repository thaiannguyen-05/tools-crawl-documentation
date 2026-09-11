#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Add current directory to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from file_process.pipeline import aggregate_chunk_vectors
from file_process.chunker import chunk_document
from file_process.errors import StorageError, UnsupportedFileError
from file_process.pipeline import chunk_to_input
from file_process.text_extractor import extract_text
from file_process.tokenizer import segment_vietnamese
from file_process.types import ChunkWithEmbedding, ExtractedDocument

logger = logging.getLogger("pipeline_processor")

SUPPORTED_EXTS = (".pdf", ".docx", ".doc", ".txt", ".md")
SKIP_SUFFIXES = (".extracted.txt",)
SKIP_FILENAMES = {"manifest.json", "training_data.csv", "training_data.pkl", "training_data_summary.json"}


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "[%(asctime)s] %(levelname)-7s: %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")


def get_encode_fn(fast_test: bool = False) -> Callable[[str], list[float]]:
    """Resolve embedding function (PhoBERT or deterministic hash vector for fast test)."""
    if fast_test:
        def _mock_encode(text: str) -> list[float]:
            import hashlib
            h = hashlib.sha256(text.encode("utf-8")).digest()
            # Generate deterministic 64-dim unit vector
            raw = [float(b) / 255.0 for b in h[:32]] + [float(b) / 255.0 for b in h[32:]]
            norm = sum(x * x for x in raw) ** 0.5 or 1.0
            return [x / norm for x in raw]
        logger.info("Using mock encoder for testing (fast mode)")
        return _mock_encode

    from model.phoBert.phobert import encode
    return encode


def discover_label_dirs(input_dir: Path) -> list[Path]:
    """Liệt kê các folder con cấp 1 làm label (bỏ qua file CSV/PKL và folder ẩn)."""
    return sorted(
        [d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))],
        key=lambda d: d.name,
    )


def collect_files_by_label(input_dir: Path, recursive: bool = True) -> dict[str, list[Path]]:
    """Quét input_dir, mỗi folder con cấp 1 là 1 label, tự vào sâu bên trong gom file.

    Ví dụ:
        input_dir/
            ai_tech/        -> label 'ai_tech' (kể cả ai_tech/sub1/file.pdf)
            economy/        -> label 'economy'
    Trả về: {label: [Path, ...]} (đã sắp xếp để chạy ổn định).
    """
    result: dict[str, list[Path]] = {}
    for label_dir in discover_label_dirs(input_dir):
        label = label_dir.name
        iterator = label_dir.rglob("*") if recursive else label_dir.iterdir()
        files: list[Path] = []
        for f in iterator:
            if not f.is_file():
                continue
            if f.name in SKIP_FILENAMES or f.name.endswith(SKIP_SUFFIXES):
                continue
            if f.suffix.lower() not in SUPPORTED_EXTS:
                continue
            files.append(f)
        files.sort(key=lambda p: p.name)
        if files:
            result[label] = files
    return result


def load_existing_csv(csv_path: Path) -> tuple[dict[str, list[list[float]]], list[dict[str, Any]], set[tuple[str, str]]]:
    """Đọc CSV cũ để gom tiếp (append) — tránh ghi trùng (label, file_name)."""
    training_data: dict[str, list[list[float]]] = {}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return training_data, rows, seen
    import csv as _csv
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                lbl = (row.get("label") or "").strip()
                fname = (row.get("file_name") or "").strip()
                if not lbl or not fname:
                    continue
                try:
                    vec = json.loads(row["vector"])
                except Exception:
                    continue
                training_data.setdefault(lbl, []).append(vec)
                rows.append({"label": lbl, "file_name": fname, "vector": vec})
                seen.add((lbl, fname))
    except Exception as e:
        logger.warning("Không đọc được CSV cũ %s: %s (sẽ ghi mới)", csv_path, e)
    return training_data, rows, seen


def process_file_to_vector(
    file_path: Path,
    encode_fn: Callable[[str], list[float]],
    method: str = "mean",
) -> dict[str, Any] | None:
    """Run a single file through the RAG pipeline up to vector aggregation.
    
    Returns a dictionary with vector, chunk count, and metadata, or None if extraction failed.
    """
    ext = file_path.suffix.lower()

    # If it's a raw .doc file, check for the .extracted.txt companion
    target_path = file_path
    if ext == ".doc":
        companion_txt = file_path.with_suffix(".extracted.txt")
        if companion_txt.exists():
            target_path = companion_txt
            ext = ".txt"
        else:
            logger.warning("Skipping legacy .doc without extracted.txt: %s", file_path.name)
            return None

    try:
        content = target_path.read_bytes()
        if not content:
            logger.warning("Empty file: %s", target_path.name)
            return None

        # 1. Extract text, headings, sections
        doc: ExtractedDocument = extract_text(target_path.name, content)
        if not doc.sections:
            logger.warning("No sections extracted from: %s", target_path.name)
            return None

        # 2. Chunk document
        chunks = chunk_document(doc)
        if not chunks:
            logger.warning("No chunks generated for: %s", target_path.name)
            return None

        # 3. Vectorize chunks with PhoBERT
        chunk_embeddings: list[list[float]] = []
        for c in chunks:
            text_input = chunk_to_input(c)
            segmented = segment_vietnamese(text_input)
            emb = encode_fn(segmented)
            chunk_embeddings.append(emb)

        # 4. Aggregate chunk vectors into a single document vector
        doc_vector = aggregate_chunk_vectors(chunk_embeddings, method=method)

        return {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "original_extension": file_path.suffix,
            "processed_file": target_path.name,
            "chunk_count": len(chunks),
            "vector": doc_vector,
            "vector_dim": len(doc_vector),
        }

    except UnsupportedFileError as e:
        logger.warning("Unsupported file %s: %s", file_path.name, e)
        return None
    except Exception as e:
        logger.error("Error processing %s: %s", file_path.name, e, exc_info=True)
        return None


def generate_training_data(
    input_dir: Path,
    output_pickle_path: Path,
    method: str = "mean",
    fast_test: bool = False,
    output_csv_path: Path | None = None,
    append: bool = True,
    recursive: bool = True,
) -> dict[str, list[list[float]]]:
    """Quét các folder con (mỗi folder = 1 label), vector hoá và gom vào cùng 1 file CSV.

    - Chỉ cần cung cấp `input_dir` (vị trí gốc chứa các folder): tự vào từng folder,
      kể cả folder lồng nhau (recursive), lấy file .pdf/.docx/.doc/.txt/.md.
    - Label = tên folder con cấp 1 (ví dụ: input_dir/ai_tech/... -> 'ai_tech').
    - `append=True` (mặc định): giữ lại dòng cũ trong CSV, chỉ thêm file mới
      (chống trùng theo cặp label + file_name). Dùng `--no-append` để ghi mới hoàn toàn.
    Output: dict[label, list[document_vectors]] + ghi CSV/PKL/summary.json.
    """
    encode_fn = get_encode_fn(fast_test=fast_test)
    if output_csv_path is None:
        output_csv_path = output_pickle_path.with_suffix(".csv")

    print("\n" + "=" * 65)
    print("⚙️  BẮT ĐẦU XỬ LÝ PIPELINE & TẠO TRAINING DATA CHO CLASSIFIER")
    print(f"📁 Thư mục dữ liệu (gốc chứa các folder): {input_dir}")
    print(f"🔁 Quét đệ quy folder con: {'BẬT' if recursive else 'TẮT'}")
    print(f"📐 Phương pháp aggregate: {method}")
    print(f"💾 File CSV đầu ra (gom chung): {output_csv_path}")
    print(f"💾 File đầu ra (pkl): {output_pickle_path}")
    print(f"➕ Chế độ gom tiếp (append): {'BẬT (giữ dòng cũ, bỏ qua file trùng)' if append else 'TẮT (ghi mới hoàn toàn)'}")
    print("=" * 65)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"⚠️ Không tìm thấy thư mục nguồn: {input_dir}")
        return {}

    # 0. Nạp CSV cũ để gom tiếp (nếu bật append)
    training_data: dict[str, list[list[float]]] = {}
    metadata_summary: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    skipped_duplicates = 0
    if append:
        training_data, old_rows, seen = load_existing_csv(output_csv_path)
        for r in old_rows:
            metadata_summary.append({
                "label": r["label"],
                "file_name": r["file_name"],
                "extension": "",
                "chunk_count": 0,
                "vector": r["vector"],
                "vector_dim": len(r["vector"]),
                "elapsed_sec": 0.0,
            })
        if old_rows:
            print(f"📥 Đã nạp {len(old_rows)} dòng cũ từ {output_csv_path} để gom tiếp.")

    # 1. Tự phát hiện các folder label và gom file bên trong
    files_by_label = collect_files_by_label(input_dir, recursive=recursive)

    if not files_by_label:
        print(f"⚠️ Không tìm thấy folder chứa tài liệu nào trong {input_dir}")
        print("   Cấu trúc đúng phải là: <input_dir>/<ten_label>/<file.pdf|docx|txt|md...>")
        print("   Ví dụ: ./my_data/ai_tech/a.pdf , ./my_data/kinh_te/b.docx")
        # Vẫn giữ file cũ nếu có (không ghi đè rỗng)
        return training_data

    print(f"🔎 Tự phát hiện {len(files_by_label)} nhãn (label = tên folder):")
    for label, files in files_by_label.items():
        print(f"   • [{label}]: {len(files)} file")

    total_files_processed = 0
    total_successful = 0
    total_new_rows = 0

    for label in sorted(files_by_label.keys()):
        files_to_process = files_by_label[label]
        print(f"\n📂 Đang xử lý nhãn (Label): [{label}] ({len(files_to_process)} file)")

        label_vectors: list[list[float]] = training_data.get(label, [])

        for file_path in files_to_process:
            # Chống trùng: cùng label + cùng tên file thì bỏ qua
            if (label, file_path.name) in seen:
                skipped_duplicates += 1
                print(f"   ⏭️ [TRÙNG - BỎ QUA] {file_path.name} (đã có trong CSV)")
                continue
            total_files_processed += 1
            try:
                rel = file_path.relative_to(input_dir)
            except ValueError:
                rel = file_path
            print(f"   ⏳ Đang chạy pipeline cho: {rel}...")
            start_t = time.time()
            res = process_file_to_vector(file_path, encode_fn=encode_fn, method=method)
            elapsed = time.time() - start_t

            if res:
                label_vectors.append(res["vector"])
                total_successful += 1
                total_new_rows += 1
                seen.add((label, res["file_name"]))
                metadata_summary.append({
                    "label": label,
                    "file_name": res["file_name"],
                    "extension": res["original_extension"],
                    "chunk_count": res["chunk_count"],
                    "vector": res["vector"],
                    "vector_dim": res["vector_dim"],
                    "elapsed_sec": round(elapsed, 2),
                })
                print(f"   ✅ [THÀNH CÔNG] {res['file_name']} -> {res['chunk_count']} chunks -> Vector {res['vector_dim']}-dim ({elapsed:.2f}s)")
            else:
                print(f"   ❌ [BỎ QUA/LỖI] {file_path.name}")

        if label_vectors:
            training_data[label] = label_vectors
            print(f"   📊 Nhãn [{label}]: Tích lũy {len(label_vectors)} vector tài liệu")

    # 1. Save training_data.pkl (pickle)
    output_pickle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_pickle_path, "wb") as f:
        pickle.dump(training_data, f)

    # 2. Save training_data.csv (dạng: vector, label, file_name) — ghi gộp toàn bộ
    import csv
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["vector", "label", "file_name"])
        for item in metadata_summary:
            writer.writerow([json.dumps(item["vector"]), item["label"], item["file_name"]])

    # 3. Save training_data_summary.json
    summary_path = output_pickle_path.with_name(f"{output_pickle_path.stem}_summary.json")
    summary_data = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aggregation_method": method,
        "source_dir": str(input_dir),
        "recursive_scan": recursive,
        "append_mode": append,
        "total_labels": len(training_data),
        "total_documents_input": total_files_processed,
        "total_vectors_new": total_new_rows,
        "total_vectors_generated": len(metadata_summary),
        "skipped_duplicates": skipped_duplicates,
        "labels": {label: len(vecs) for label, vecs in training_data.items()},
        "documents": [
            {k: v for k, v in doc.items() if k != "vector"}
            for doc in metadata_summary
        ],
    }
    summary_path.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 65)
    print("🎉 HOÀN TẤT TẠO TRAINING DATA!")
    print("=" * 65)
    for label, vecs in training_data.items():
        dim = len(vecs[0]) if vecs else 0
        print(f"  🏷️ Nhãn [{label}]: {len(vecs)} bản ghi vector (Kích thước: {dim} chiều)")

    print(f"\n📊 File mới xử lý: {total_files_processed} | Thêm mới: {total_new_rows} | Bỏ qua trùng: {skipped_duplicates}")
    print(f"💾 File Training Data CSV:    {output_csv_path} ({len(metadata_summary)} dòng)")
    print(f"💾 File Training Data Pickle: {output_pickle_path}")
    print(f"📄 File Báo cáo chi tiết JSON: {summary_path}")
    print(f"🚀 Sẵn sàng đưa vào: build_classifier(training_data, method='{method}')")

    return training_data


def load_training_data_from_csv(csv_path: Path | str) -> dict[str, list[list[float]]]:
    """Đọc dữ liệu training từ file CSV (vector, label) chuẩn bị cho classifier."""
    import csv
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file CSV: {path}")

    training_data: dict[str, list[list[float]]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lbl = row["label"]
            vec_raw = row["vector"]
            vec = json.loads(vec_raw)
            if lbl not in training_data:
                training_data[lbl] = []
            training_data[lbl].append(vec)

    return training_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG Pipeline Processor - Chạy pipeline bóc tách, chunk, PhoBERT vector hóa và gắn nhãn Training Data cho Classifier."
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(CURRENT_DIR / "output"),
        help="Vị trí gốc chứa các folder (mỗi folder con = 1 label). Ví dụ: ./my_data với ./my_data/ai_tech/*.pdf (Mặc định: ./output).",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="Alias của --input-dir: vị trí lưu các folder có sẵn chứa file.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(CURRENT_DIR / "output" / "training_data.pkl"),
        help="Đường dẫn lưu file training_data.pkl (Mặc định: ./output/training_data.pkl).",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Đường dẫn file CSV gom chung (Mặc định: cùng thư mục với --output-file, tên training_data.csv).",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["mean", "max", "weighted"],
        default="mean",
        help="Phương pháp aggregate các vector chunk thành vector tài liệu (Mặc định: mean).",
    )
    parser.add_argument(
        "--fast-test",
        action="store_true",
        help="Chế độ kiểm thử nhanh (dùng mock vector thay vì tải mô hình PhoBERT nặng).",
    )
    parser.add_argument(
        "--no-append",
        action="store_true",
        help="Ghi mới hoàn toàn CSV/PKL (mặc định là gom tiếp: giữ dòng cũ, bỏ qua file trùng).",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Chỉ quét file ở ngay trong folder label, không vào folder lồng nhau.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Bật log chi tiết debug.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    input_dir = Path(args.source_dir) if args.source_dir else Path(args.input_dir)
    output_pickle_path = Path(args.output_file)
    output_csv_path = Path(args.output_csv) if args.output_csv else output_pickle_path.with_suffix(".csv")

    generate_training_data(
        input_dir=input_dir,
        output_pickle_path=output_pickle_path,
        method=args.method,
        fast_test=args.fast_test,
        output_csv_path=output_csv_path,
        append=not args.no_append,
        recursive=not args.no_recursive,
    )


if __name__ == "__main__":
    main()
