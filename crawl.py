#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path for standalone execution on any machine
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import FAMOUS_TOPICS, SUPPORTED_FORMATS, TopicDefinition
from downloader import download_document
from sources.ddg_search import search_ddg_files
from sources.github_source import search_github_markdown
from sources.wiki_source import search_wiki_articles

import csv
from collections.abc import Callable

logger = logging.getLogger("doc_crawler")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "[%(asctime)s] %(levelname)-7s: %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")


def _handle_document_record(
    res: dict,
    topic_dir: Path,
    topic_slug: str,
    encode_fn: Callable[[str], list[float]] | None,
    output_csv_path: Path | None,
    delete_raw: bool,
    downloaded_items: list[dict],
    target_records: int,
) -> bool:
    """Process a downloaded file into a vector, append to CSV, and delete raw file if requested."""
    file_path = topic_dir / res["file_name"]

    if encode_fn is not None and output_csv_path is not None:
        from processor import process_file_to_vector

        vec_info = process_file_to_vector(file_path, encode_fn=encode_fn, method="mean")
        if vec_info:
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not output_csv_path.exists() or output_csv_path.stat().st_size == 0
            with open(output_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["vector", "label", "file_name"])
                writer.writerow([json.dumps(vec_info["vector"]), topic_slug, vec_info["file_name"]])
                f.flush()

            if delete_raw:
                file_path.unlink(missing_ok=True)
                companion = file_path.with_suffix(".extracted.txt")
                companion.unlink(missing_ok=True)
                print(
                    f"   ✅ [VECTƠ HOÁ & ĐÃ XÓA FILE THÔ] {res['file_name']} -> {vec_info['chunk_count']} chunks "
                    f"({vec_info['vector_dim']}-dim) -> Lưu CSV [{len(downloaded_items) + 1}/{target_records}]"
                )
            else:
                print(
                    f"   ✅ [VECTƠ HOÁ] {res['file_name']} -> {vec_info['chunk_count']} chunks "
                    f"({vec_info['vector_dim']}-dim) -> Lưu CSV [{len(downloaded_items) + 1}/{target_records}]"
                )

            downloaded_items.append(res)
            return True
        else:
            if delete_raw:
                file_path.unlink(missing_ok=True)
                companion = file_path.with_suffix(".extracted.txt")
                companion.unlink(missing_ok=True)
            print(f"   ⚠️ [BỎ QUA & ĐÃ XÓA FILE HỎNG] {res['file_name']}")
            return False
    else:
        converted_info = f" -> Converted: {Path(res['converted_file']).name}" if res.get("converted_file") else ""
        print(f"   ✅ [{res.get('format', 'FILE').upper()}] {res['file_name']} ({res['size']:,} bytes){converted_info} - [{len(downloaded_items) + 1}/{target_records}]")
        downloaded_items.append(res)
        return True


def crawl_single_topic(
    topic_key_or_name: str,
    formats: list[str],
    target_records: int,
    output_base_dir: Path,
    encode_fn: Callable[[str], list[float]] | None = None,
    output_csv_path: Path | None = None,
    delete_raw: bool = False,
) -> dict:
    """Crawl documents for a single topic with exact target records limit and optional streaming vectorization."""
    if topic_key_or_name in FAMOUS_TOPICS:
        topic_def = FAMOUS_TOPICS[topic_key_or_name]
        topic_slug = topic_def.key
        topic_display = topic_def.name
        search_terms = topic_def.search_keywords
        github_terms = topic_def.github_queries
        wiki_terms = topic_def.wiki_queries
    else:
        topic_slug = topic_key_or_name.lower().replace(" ", "_")
        topic_display = topic_key_or_name
        search_terms = [topic_key_or_name]
        github_terms = [topic_key_or_name]
        wiki_terms = [topic_key_or_name]

    topic_dir = output_base_dir / topic_slug
    topic_dir.mkdir(parents=True, exist_ok=True)

    mode_note = " (Chế độ xử lý trực tiếp & Xóa file thô)" if (encode_fn and delete_raw) else ""
    print(f"\n=======================================================")
    print(f"🎯 Chủ đề: {topic_display}{mode_note}")
    print(f"📊 Mục tiêu: {target_records} bản ghi")
    print(f"📁 Thư mục lưu trữ: {topic_dir}")
    print(f"📄 Các định dạng: {', '.join(formats)}")
    print(f"=======================================================")

    manifest_path = topic_dir / "manifest.json"
    downloaded_items: list[dict] = []
    seen_urls: set[str] = set()

    if manifest_path.exists():
        try:
            existing_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in existing_data.get("documents", []):
                seen_urls.add(item.get("url"))
        except Exception:
            pass

    # Read already saved filenames from CSV to avoid duplicates
    if output_csv_path and output_csv_path.exists():
        try:
            with open(output_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("label") == topic_slug:
                        seen_urls.add(row.get("file_name", ""))
        except Exception:
            pass

    # Calculate target quota per format
    base_per_format = max(1, math.ceil(target_records / max(len(formats), 1)))

    for fmt in formats:
        if len(downloaded_items) >= target_records:
            break

        fmt_clean = fmt.lower().lstrip(".")
        remaining_needed = target_records - len(downloaded_items)
        quota_for_this_format = min(base_per_format, remaining_needed)

        print(f"\n🔍 [Định dạng .{fmt_clean}] Đang tìm kiếm (Chỉ tiêu: {quota_for_this_format} bản ghi)...")
        downloaded_for_fmt = 0

        # 1. Special handler for Markdown (.md)
        if fmt_clean == "md":
            for term in github_terms:
                if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                    break
                logger.info("Searching GitHub for markdown: '%s'", term)
                md_candidates = search_github_markdown(term, max_results=quota_for_this_format)
                for cand in md_candidates:
                    if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                        break
                    url = cand["url"]
                    if url in seen_urls:
                        continue
                    res = download_document(
                        url=url,
                        output_dir=topic_dir,
                        file_format="md",
                        title=cand["title"],
                    )
                    if res:
                        seen_urls.add(url)
                        if _handle_document_record(
                            res, topic_dir, topic_slug, encode_fn, output_csv_path,
                            delete_raw, downloaded_items, target_records
                        ):
                            downloaded_for_fmt += 1
                        time.sleep(0.3)

        # 2. Special handler for Plain Text (.txt) via Wikipedia
        if fmt_clean == "txt":
            for term in wiki_terms:
                if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                    break
                logger.info("Searching Wikipedia for text: '%s'", term)
                wiki_candidates = search_wiki_articles(term, max_results=quota_for_this_format)
                for cand in wiki_candidates:
                    if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                        break
                    url = cand["url"]
                    if url in seen_urls:
                        continue
                    res = download_document(
                        url=url,
                        output_dir=topic_dir,
                        file_format="txt",
                        title=cand["title"],
                        direct_content=cand.get("direct_content"),
                    )
                    if res:
                        seen_urls.add(url)
                        if _handle_document_record(
                            res, topic_dir, topic_slug, encode_fn, output_csv_path,
                            delete_raw, downloaded_items, target_records
                        ):
                            downloaded_for_fmt += 1
                        time.sleep(0.3)

        # 3. DuckDuckGo search for PDF, DOCX, DOC and others
        for term in search_terms:
            if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                break
            logger.info("Searching DDG for .%s: '%s'", fmt_clean, term)
            candidates = search_ddg_files(term, file_format=fmt_clean, max_results=quota_for_this_format * 2)
            for cand in candidates:
                if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                    break
                url = cand["url"]
                if url in seen_urls:
                    continue
                res = download_document(
                    url=url,
                    output_dir=topic_dir,
                    file_format=fmt_clean,
                    title=cand["title"],
                )
                if res:
                    seen_urls.add(url)
                    if _handle_document_record(
                        res, topic_dir, topic_slug, encode_fn, output_csv_path,
                        delete_raw, downloaded_items, target_records
                    ):
                        downloaded_for_fmt += 1
                    time.sleep(0.4)

        # 4. Fallback to curated seeds if format is still below quota
        if downloaded_for_fmt < quota_for_this_format and len(downloaded_items) < target_records:
            if topic_key_or_name in FAMOUS_TOPICS:
                topic_def = FAMOUS_TOPICS[topic_key_or_name]
                seeds = topic_def.curated_seeds.get(fmt_clean, [])
                for seed_url, seed_title in seeds:
                    if downloaded_for_fmt >= quota_for_this_format or len(downloaded_items) >= target_records:
                        break
                    if seed_url in seen_urls:
                        continue
                    res = download_document(
                        url=seed_url,
                        output_dir=topic_dir,
                        file_format=fmt_clean,
                        title=seed_title,
                    )
                    if res:
                        seen_urls.add(seed_url)
                        if _handle_document_record(
                            res, topic_dir, topic_slug, encode_fn, output_csv_path,
                            delete_raw, downloaded_items, target_records
                        ):
                            downloaded_for_fmt += 1
                        time.sleep(0.3)

        print(f"   📊 Định dạng .{fmt_clean}: hoàn thành {downloaded_for_fmt} bản ghi (Tổng tích lũy: {len(downloaded_items)}/{target_records})")

    # 5. Catch-up loop: If still below target_records, fulfill remainder using Wikipedia (.txt) and DuckDuckGo (.pdf)
    if len(downloaded_items) < target_records:
        shortfall = target_records - len(downloaded_items)
        print(f"\n🔄 [BỔ SUNG CHỈ TIÊU] Đang tìm kiếm thêm {shortfall} bản ghi từ Wikipedia và PDF...")

        for term in wiki_terms:
            if len(downloaded_items) >= target_records:
                break
            wiki_more = search_wiki_articles(term, max_results=min(100, target_records - len(downloaded_items)))
            for cand in wiki_more:
                if len(downloaded_items) >= target_records:
                    break
                url = cand["url"]
                if url in seen_urls:
                    continue
                res = download_document(
                    url=url,
                    output_dir=topic_dir,
                    file_format="txt",
                    title=cand["title"],
                    direct_content=cand.get("direct_content"),
                )
                if res:
                    seen_urls.add(url)
                    _handle_document_record(
                        res, topic_dir, topic_slug, encode_fn, output_csv_path,
                        delete_raw, downloaded_items, target_records
                    )
                    time.sleep(0.2)

        for term in search_terms:
            if len(downloaded_items) >= target_records:
                break
            ddg_more = search_ddg_files(term, file_format="pdf", max_results=min(50, target_records - len(downloaded_items)))
            for cand in ddg_more:
                if len(downloaded_items) >= target_records:
                    break
                url = cand["url"]
                if url in seen_urls:
                    continue
                res = download_document(
                    url=url,
                    output_dir=topic_dir,
                    file_format="pdf",
                    title=cand["title"],
                )
                if res:
                    seen_urls.add(url)
                    _handle_document_record(
                        res, topic_dir, topic_slug, encode_fn, output_csv_path,
                        delete_raw, downloaded_items, target_records
                    )
                    time.sleep(0.3)

    # Clean up directory if delete_raw is requested
    if delete_raw:
        manifest_path.unlink(missing_ok=True)
        # Remove any stray files left in topic_dir
        for f in topic_dir.iterdir():
            if f.is_file():
                f.unlink(missing_ok=True)
        try:
            topic_dir.rmdir()
        except OSError:
            pass
        print(f"🧹 Đã dọn dẹp thư mục tạm và xóa sạch file thô của chủ đề [{topic_slug}]")
    else:
        manifest_data = {
            "topic_key": topic_slug,
            "topic_name": topic_display,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_documents": len(downloaded_items),
            "target_requested": target_records,
            "documents": downloaded_items,
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n💾 Đã cập nhật danh mục ({len(downloaded_items)} bản ghi) vào: {manifest_path}")

    return {
        "topic_key": topic_slug,
        "total_documents": len(downloaded_items),
        "target_requested": target_records,
    }


def prompt_int(prompt: str, default: int, min_val: int = 1) -> int:
    """Prompt user for an integer with default fallback."""
    while True:
        try:
            val_str = input(f"{prompt} [Mặc định: {default}]: ").strip()
            if not val_str:
                return default
            val = int(val_str)
            if val < min_val:
                print(f"⚠️ Vui lòng nhập số >= {min_val}")
                continue
            return val
        except ValueError:
            print("⚠️ Vui lòng nhập một số nguyên hợp lệ.")


def interactive_cli(output_base_dir: Path) -> None:
    """Interactive CLI menu to pick topics and set record counts."""
    print("\n" + "=" * 65)
    print("🕷️  CÔNG CỤ CRAWLER TÀI LIỆU ĐA ĐỊNH DẠNG (CLI INTERACTIVE)")
    print("=" * 65)
    print("Danh sách 5 chủ đề nổi tiếng (Famous Topics):")
    topics_keys = list(FAMOUS_TOPICS.keys())
    for idx, key in enumerate(topics_keys, 1):
        item = FAMOUS_TOPICS[key]
        print(f"  [{idx}] {item.name} ({key})")

    print("\nChọn chế độ hoạt động:")
    print("  [1] Chọn từng chủ đề cụ thể và nhập số lượng bản ghi riêng")
    print("  [2] Crawl toàn bộ 5 chủ đề nổi tiếng (Nhập số lượng cho mỗi chủ đề)")
    print("  [3] Nhập một chủ đề tùy chỉnh mới")
    print("  [4] Đã có sẵn folder chứa file -> nhập vị trí, tự quét & gom ra training_data.csv")
    print("  [0] Thoát")
    print("-" * 65)

    choice = input("👉 Nhập lựa chọn của bạn (0-4): ").strip()
    if choice == "0":
        print("Tạm biệt!")
        sys.exit(0)

    # Mode 1: Pick specific topics and set individual counts
    if choice == "1":
        print("\nNhập số thứ tự các chủ đề muốn chọn (ví dụ: 1, 3 hoặc 1-3 hoặc all):")
        selection = input("👉 Chọn chủ đề: ").strip().lower()
        selected_keys: list[str] = []

        if selection in ("all", "*"):
            selected_keys = topics_keys[:]
        else:
            parts = [p.strip() for p in selection.replace(",", " ").split() if p.strip()]
            for part in parts:
                if "-" in part:
                    try:
                        start_s, end_s = part.split("-", 1)
                        s_idx, e_idx = int(start_s), int(end_s)
                        for i in range(s_idx, e_idx + 1):
                            if 1 <= i <= len(topics_keys) and topics_keys[i - 1] not in selected_keys:
                                selected_keys.append(topics_keys[i - 1])
                    except ValueError:
                        pass
                else:
                    try:
                        idx = int(part)
                        if 1 <= idx <= len(topics_keys) and topics_keys[idx - 1] not in selected_keys:
                            selected_keys.append(topics_keys[idx - 1])
                    except ValueError:
                        if part in FAMOUS_TOPICS and part not in selected_keys:
                            selected_keys.append(part)

        if not selected_keys:
            print("⚠️ Không có chủ đề nào được chọn.")
            return

        # Prompt count for each selected topic
        topic_counts: dict[str, int] = {}
        print("\n--- Thiết lập số lượng bản ghi cho từng chủ đề ---")
        for key in selected_keys:
            name = FAMOUS_TOPICS[key].name
            count = prompt_int(f"👉 Số lượng bản ghi cho '{name}'", default=5)
            topic_counts[key] = count

        ask_proc = input("\n👉 Bạn có muốn chạy Pipeline xử lý vector và xuất training_data.csv ngay bây giờ? [Y/n]: ").strip().lower()
        auto_proc = ask_proc in ("", "y", "yes")
        del_raw = False
        if auto_proc:
            ask_del = input("👉 Bạn có muốn tự động XÓA FILE THÔ sau khi xử lý (chỉ để lại training_data.csv)? [Y/n]: ").strip().lower()
            del_raw = ask_del in ("", "y", "yes")

        _execute_crawl_batch(topic_counts, SUPPORTED_FORMATS, output_base_dir, auto_process=auto_proc, delete_raw=del_raw)

    # Mode 2: Crawl all 5 famous topics
    elif choice == "2":
        print("\n--- Crawl toàn bộ 5 chủ đề nổi tiếng ---")
        sub_choice = input("👉 Bạn muốn [1] Dùng cùng 1 số lượng cho tất cả, hay [2] Nhập riêng từng chủ đề? [1/2, Mặc định 1]: ").strip()
        topic_counts = {}
        if sub_choice == "2":
            for key in topics_keys:
                name = FAMOUS_TOPICS[key].name
                count = prompt_int(f"👉 Số lượng bản ghi cho '{name}'", default=5)
                topic_counts[key] = count
        else:
            default_all = prompt_int("👉 Nhập số lượng bản ghi cho MỖI chủ đề", default=5)
            for key in topics_keys:
                topic_counts[key] = default_all

        ask_proc = input("\n👉 Bạn có muốn chạy Pipeline xử lý vector và xuất training_data.csv ngay bây giờ? [Y/n]: ").strip().lower()
        auto_proc = ask_proc in ("", "y", "yes")
        del_raw = False
        if auto_proc:
            ask_del = input("👉 Bạn có muốn tự động XÓA FILE THÔ sau khi xử lý (chỉ để lại training_data.csv)? [Y/n]: ").strip().lower()
            del_raw = ask_del in ("", "y", "yes")

        _execute_crawl_batch(topic_counts, SUPPORTED_FORMATS, output_base_dir, auto_process=auto_proc, delete_raw=del_raw)

    # Mode 3: Custom topic
    elif choice == "3":
        custom_topic = input("👉 Nhập từ khóa / tên chủ đề cần crawl: ").strip()
        if not custom_topic:
            print("⚠️ Tên chủ đề không được để trống.")
            return
        count = prompt_int(f"👉 Số lượng bản ghi cần crawl cho '{custom_topic}'", default=5)
        
        ask_proc = input("\n👉 Bạn có muốn chạy Pipeline xử lý vector và xuất training_data.csv ngay bây giờ? [Y/n]: ").strip().lower()
        auto_proc = ask_proc in ("", "y", "yes")
        del_raw = False
        if auto_proc:
            ask_del = input("👉 Bạn có muốn tự động XÓA FILE THÔ sau khi xử lý (chỉ để lại training_data.csv)? [Y/n]: ").strip().lower()
            del_raw = ask_del in ("", "y", "yes")

        topic_counts = {custom_topic: count}
        _execute_crawl_batch(topic_counts, SUPPORTED_FORMATS, output_base_dir, auto_process=auto_proc, delete_raw=del_raw)

    # Mode 4: Đã có sẵn folder chứa file -> chỉ cần nhập vị trí, tự quét & gom CSV
    elif choice == "4":
        print("\n--- Xử lý folder có sẵn (mỗi folder con = 1 label) ---")
        print("   Ví dụ cấu trúc đúng:")
        print("     D:/du_lieu/ai_tech/a.pdf")
        print("     D:/du_lieu/kinh_te/b.docx")
        raw_src = input("👉 Nhập vị trí folder gốc chứa các folder (Mặc định: ./output): ").strip()
        source_dir = Path(raw_src) if raw_src else output_base_dir
        raw_csv = input(f"👉 File CSV gom chung [Mặc định: {output_base_dir / 'training_data.csv'}]: ").strip()
        output_csv = Path(raw_csv) if raw_csv else (output_base_dir / "training_data.csv")
        ask_append = input("👉 Gom tiếp vào CSV cũ nếu có? (giữ dòng cũ, bỏ qua file trùng) [Y/n]: ").strip().lower()
        use_append = ask_append in ("", "y", "yes")
        ask_rec = input("👉 Quét cả folder lồng nhau bên trong? [Y/n]: ").strip().lower()
        use_recursive = ask_rec in ("", "y", "yes")
        _execute_local_folders(source_dir, output_csv, append=use_append, recursive=use_recursive)

    else:
        print("⚠️ Lựa chọn không hợp lệ.")


def _execute_local_folders(
    source_dir: Path,
    output_csv_path: Path,
    method: str = "mean",
    fast_test: bool = False,
    append: bool = True,
    recursive: bool = True,
) -> None:
    """Vector hoá các folder có sẵn: mỗi folder con = 1 label, gom vào cùng 1 CSV."""
    from processor import generate_training_data

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"⚠️ Không tìm thấy thư mục nguồn: {source_dir}")
        return
    output_pickle_path = output_csv_path.with_suffix(".pkl")
    print("\n🚀 BẮT ĐẦU XỬ LÝ FOLDER CÓ SẴN...")
    print(f"📁 Vị trí folder gốc: {source_dir}")
    print(f"💾 File CSV gom chung: {output_csv_path}")
    generate_training_data(
        input_dir=source_dir,
        output_pickle_path=output_pickle_path,
        method=method,
        fast_test=fast_test,
        output_csv_path=output_csv_path,
        append=append,
        recursive=recursive,
    )


def _execute_crawl_batch(
    topic_counts: dict[str, int],
    formats: list[str],
    output_base_dir: Path,
    auto_process: bool = False,
    delete_raw: bool = False,
    fast_test: bool = False,
    output_csv_path: Path | None = None,
) -> None:
    """Execute crawling for a mapping of topic -> target_records with optional streaming vectorization."""
    if output_csv_path is None:
        output_csv_path = output_base_dir / "training_data.csv"

    # If delete_raw is requested, auto_process must be True
    if delete_raw:
        auto_process = True

    encode_fn = None
    if auto_process:
        from processor import get_encode_fn
        print("\n⚙️ Đang khởi tạo mô hình vector hoá (PhoBERT)...")
        encode_fn = get_encode_fn(fast_test=fast_test)

    print("\n🚀 BẮT ĐẦU TIẾN TRÌNH CRAWL...")
    summary = {}
    total_requested = sum(topic_counts.values())
    total_downloaded = 0

    for key, count in topic_counts.items():
        res = crawl_single_topic(
            topic_key_or_name=key,
            formats=formats,
            target_records=count,
            output_base_dir=output_base_dir,
            encode_fn=encode_fn,
            output_csv_path=output_csv_path,
            delete_raw=delete_raw,
        )
        downloaded = res["total_documents"]
        summary[key] = (downloaded, count)
        total_downloaded += downloaded
        time.sleep(0.3)

    # Clean up empty directories in output_base_dir if delete_raw is set
    if delete_raw:
        for sub_dir in output_base_dir.iterdir():
            if sub_dir.is_dir():
                try:
                    # Remove any empty subdirectories
                    sub_dir.rmdir()
                except OSError:
                    pass

    print("\n" + "=" * 65)
    print("🎉 HOÀN TẤT TIẾN TRÌNH CRAWL & VECTOR HOÁ!")
    print("=" * 65)
    for key, (done, target) in summary.items():
        name = FAMOUS_TOPICS[key].name if key in FAMOUS_TOPICS else key
        status_mark = "✅" if done >= target else "⚠️"
        print(f"  {status_mark} {name}: {done}/{target} bản ghi")

    print(f"\n📊 Tổng cộng đã hoàn thành: {total_downloaded}/{total_requested} bản ghi")
    if delete_raw:
        print("🧹 Tất cả file tài liệu thô đã được xóa sạch sau khi vector hóa.")
        print(f"💾 File Training Data duy nhất được lưu tại: {output_csv_path}")
    else:
        print(f"📁 Dữ liệu tài liệu được lưu tại: {output_base_dir}")
        if auto_process:
            print(f"💾 File Training Data CSV: {output_csv_path}")


def parse_topic_counts_arg(arg_str: str) -> dict[str, int]:
    """Parse format like 'ai_tech=10,economy_finance=5'."""
    result: dict[str, int] = {}
    pairs = [p.strip() for p in arg_str.split(",") if p.strip()]
    for p in pairs:
        if "=" in p:
            k, v = p.split("=", 1)
            try:
                result[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone Document Crawler - Thu thập tài liệu doc, docx, pdf, txt, md theo chủ đề."
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Chạy giao diện tương tác CLI (cho phép chọn chủ đề và số bản ghi trực tiếp trên màn hình).",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Chủ đề cần crawl (tên chủ đề hoặc key trong 5 chủ đề famous).",
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=None,
        help="Số lượng bản ghi cần crawl cho chủ đề (Mặc định: 5 bản ghi).",
    )
    parser.add_argument(
        "--crawl-5-famous",
        action="store_true",
        help="Tự động thu thập toàn bộ 5 chủ đề nổi tiếng.",
    )
    parser.add_argument(
        "--topic-counts",
        type=str,
        help="Chỉ định số lượng bản ghi riêng cho từng chủ đề (Ví dụ: 'ai_tech=10,economy_finance=5,health_medicine=3').",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=SUPPORTED_FORMATS,
        help=f"Danh sách các định dạng cần crawl (Mặc định: {', '.join(SUPPORTED_FORMATS)}).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(CURRENT_DIR / "output"),
        help="Thư mục gốc lưu trữ dữ liệu tải về (Mặc định: ./output).",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Đường dẫn file CSV xuất dữ liệu huấn luyện (Mặc định: <output-dir>/training_data.csv).",
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="Hiển thị danh sách 5 chủ đề nổi tiếng có sẵn.",
    )
    parser.add_argument(
        "--process",
        "-p",
        action="store_true",
        help="Tự động chạy pipeline RAG xử lý vector và xuất training_data.csv ngay khi crawl.",
    )
    parser.add_argument(
        "--delete-raw",
        action="store_true",
        help="Xóa tệp thô ngay sau khi xử lý vector xong, chỉ để lại file CSV đầu ra để tiết kiệm ổ cứng.",
    )
    parser.add_argument(
        "--fast-test",
        action="store_true",
        help="Dùng mock encoder để kiểm thử quy trình nhanh mà không cần tải mô hình PhoBERT.",
    )
    parser.add_argument(
        "--from-folders",
        type=str,
        default=None,
        help="Đã có sẵn folder chứa file: chỉ cần chỉ vị trí gốc (mỗi folder con = 1 label), tự quét & gom ra CSV. Ví dụ: --from-folders ./my_data",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["mean", "max", "weighted"],
        default="mean",
        help="Phương pháp aggregate vector khi dùng --from-folders (Mặc định: mean).",
    )
    parser.add_argument(
        "--no-append",
        action="store_true",
        help="Khi dùng --from-folders: ghi mới hoàn toàn CSV (mặc định gom tiếp, bỏ qua file trùng).",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Khi dùng --from-folders: chỉ quét file ngay trong folder label, không vào folder lồng nhau.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Bật log chi tiết debug.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    output_base_dir = Path(args.output_dir)
    output_csv_path = Path(args.output_csv) if args.output_csv else output_base_dir / "training_data.csv"
    delete_raw = args.delete_raw
    auto_process = args.process or delete_raw

    # 1. List topics flag
    if args.list_topics:
        print("\n📚 DANH SÁCH 5 CHỦ ĐỀ NỔI TIẾNG (FAMOUS TOPICS):")
        print("-----------------------------------------------------------------")
        for key, item in FAMOUS_TOPICS.items():
            print(f"  • [{key}]: {item.name}")
            print(f"    Mô tả: {item.description}")
            print(f"    Từ khóa mẫu: {', '.join(item.search_keywords[:3])}\n")
        sys.exit(0)

    # 1b. Đã có sẵn folder chứa file -> chỉ cần vị trí, tự quét & gom CSV
    if args.from_folders:
        _execute_local_folders(
            Path(args.from_folders),
            output_csv_path,
            method=args.method,
            fast_test=args.fast_test,
            append=not args.no_append,
            recursive=not args.no_recursive,
        )
        sys.exit(0)

    # 2. Topic counts argument: 'ai_tech=10,economy_finance=5'
    if args.topic_counts:
        counts = parse_topic_counts_arg(args.topic_counts)
        if not counts:
            print("⚠️ Tham số --topic-counts không hợp lệ. Ví dụ: --topic-counts 'ai_tech=10,economy_finance=5'")
            sys.exit(1)
        _execute_crawl_batch(
            counts, args.formats, output_base_dir,
            auto_process=auto_process, delete_raw=delete_raw,
            fast_test=args.fast_test, output_csv_path=output_csv_path,
        )
        sys.exit(0)

    # 3. Crawl 5 famous with specific count
    if args.crawl_5_famous:
        target = args.count if args.count is not None else 5
        counts = {key: target for key in FAMOUS_TOPICS}
        _execute_crawl_batch(
            counts, args.formats, output_base_dir,
            auto_process=auto_process, delete_raw=delete_raw,
            fast_test=args.fast_test, output_csv_path=output_csv_path,
        )
        sys.exit(0)

    # 4. Single topic with count
    if args.topic:
        target = args.count if args.count is not None else 5
        counts = {args.topic: target}
        _execute_crawl_batch(
            counts, args.formats, output_base_dir,
            auto_process=auto_process, delete_raw=delete_raw,
            fast_test=args.fast_test, output_csv_path=output_csv_path,
        )
        sys.exit(0)

    # 5. Default: Interactive CLI Wizard
    interactive_cli(output_base_dir)


if __name__ == "__main__":
    main()
