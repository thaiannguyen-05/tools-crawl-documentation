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
) -> dict[str, list[list[float]]]:
    """Scan crawled topic directories, run pipeline, and output labeled training data.
    
    Output format:
        training_data: dict[label, list[document_vectors]]
    This format directly feeds into classifier.build_classifier(training_data).
    """
    encode_fn = get_encode_fn(fast_test=fast_test)

    print("\n" + "=" * 65)
    print("⚙️  BẮT ĐẦU XỬ LÝ PIPELINE & TẠO TRAINING DATA CHO CLASSIFIER")
    print(f"📁 Thư mục dữ liệu: {input_dir}")
    print(f"📐 Phương pháp aggregate: {method}")
    print(f"💾 File đầu ra: {output_pickle_path}")
    print("=" * 65)

    training_data: dict[str, list[list[float]]] = {}
    metadata_summary: list[dict[str, Any]] = []

    # Find all subdirectories (each is a topic/category label)
    topic_dirs = [d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]

    if not topic_dirs:
        print(f"⚠️ Không tìm thấy thư mục chủ đề nào trong {input_dir}")
        return {}

    total_files_processed = 0
    total_successful = 0

    for topic_dir in sorted(topic_dirs, key=lambda d: d.name):
        label = topic_dir.name
        print(f"\n📂 Đang xử lý nhãn (Label): [{label}] tại {topic_dir.name}/")

        # Collect candidate document files (skip manifest.json and helper extracted files to avoid duplicate)
        files_to_process: list[Path] = []
        for file in topic_dir.iterdir():
            if not file.is_file():
                continue
            if file.name.endswith((".extracted.txt", "manifest.json")):
                continue
            if file.suffix.lower() in (".pdf", ".docx", ".doc", ".txt", ".md"):
                files_to_process.append(file)

        if not files_to_process:
            print(f"   ⚠️ Không tìm thấy tệp tài liệu trong {topic_dir.name}/")
            continue

        label_vectors: list[list[float]] = []

        for file_path in files_to_process:
            total_files_processed += 1
            print(f"   ⏳ Đang chạy pipeline cho: {file_path.name}...")
            start_t = time.time()
            res = process_file_to_vector(file_path, encode_fn=encode_fn, method=method)
            elapsed = time.time() - start_t

            if res:
                label_vectors.append(res["vector"])
                total_successful += 1
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

    # 2. Save training_data.csv (dạng: vector, label, file_name)
    import csv
    output_csv_path = output_pickle_path.with_suffix(".csv")
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
        "total_labels": len(training_data),
        "total_documents_input": total_files_processed,
        "total_vectors_generated": total_successful,
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

    print(f"\n💾 File Training Data CSV:    {output_csv_path}")
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
        help="Thư mục chứa các tệp đã crawl theo từng chủ đề (Mặc định: ./output).",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(CURRENT_DIR / "output" / "training_data.pkl"),
        help="Đường dẫn lưu file training_data.pkl (Mặc định: ./output/training_data.pkl).",
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
        "-v",
        "--verbose",
        action="store_true",
        help="Bật log chi tiết debug.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    input_dir = Path(args.input_dir)
    output_pickle_path = Path(args.output_file)

    generate_training_data(
        input_dir=input_dir,
        output_pickle_path=output_pickle_path,
        method=args.method,
        fast_test=args.fast_test,
    )


if __name__ == "__main__":
    main()
