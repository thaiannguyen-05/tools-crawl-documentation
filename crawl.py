#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
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

logger = logging.getLogger("doc_crawler")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "[%(asctime)s] %(levelname)-7s: %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")


def crawl_single_topic(
    topic_key_or_name: str,
    formats: list[str],
    limit_per_format: int,
    output_base_dir: Path,
) -> dict:
    """Crawl documents for a single topic across specified formats."""
    # Check if pre-defined or custom topic
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

    print(f"\n=======================================================")
    print(f"🎯 Đang thu thập chủ đề: {topic_display}")
    print(f"📁 Thư mục lưu trữ: {topic_dir}")
    print(f"📄 Các định dạng: {', '.join(formats)}")
    print(f"=======================================================")

    manifest_path = topic_dir / "manifest.json"
    downloaded_items: list[dict] = []
    seen_urls: set[str] = set()

    # If manifest already exists, load existing URLs
    if manifest_path.exists():
        try:
            existing_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in existing_data.get("documents", []):
                seen_urls.add(item.get("url"))
        except Exception:
            pass

    for fmt in formats:
        fmt_clean = fmt.lower().lstrip(".")
        print(f"\n🔍 [Định dạng .{fmt_clean}] Bắt đầu tìm kiếm...")
        downloaded_for_fmt = 0

        # Special handler for Markdown (.md)
        if fmt_clean == "md":
            for term in github_terms:
                if downloaded_for_fmt >= limit_per_format:
                    break
                logger.info("Searching GitHub for markdown: '%s'", term)
                md_candidates = search_github_markdown(term, max_results=limit_per_format)
                for cand in md_candidates:
                    if downloaded_for_fmt >= limit_per_format:
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
                        downloaded_items.append(res)
                        downloaded_for_fmt += 1
                        print(f"   ✅ [MD] {res['file_name']} ({res['size']:,} bytes)")
                        time.sleep(0.5)

        # Special handler for Plain Text (.txt) via Wikipedia
        if fmt_clean == "txt":
            for term in wiki_terms:
                if downloaded_for_fmt >= limit_per_format:
                    break
                logger.info("Searching Wikipedia for text: '%s'", term)
                wiki_candidates = search_wiki_articles(term, max_results=limit_per_format)
                for cand in wiki_candidates:
                    if downloaded_for_fmt >= limit_per_format:
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
                        downloaded_items.append(res)
                        downloaded_for_fmt += 1
                        print(f"   ✅ [TXT] {res['file_name']} ({res['size']:,} bytes)")
                        time.sleep(0.5)

        # DuckDuckGo search for PDF, DOCX, DOC and additional TXT/MD
        for term in search_terms:
            if downloaded_for_fmt >= limit_per_format:
                break
            logger.info("Searching DDG for .%s: '%s'", fmt_clean, term)
            candidates = search_ddg_files(term, file_format=fmt_clean, max_results=limit_per_format * 2)
            for cand in candidates:
                if downloaded_for_fmt >= limit_per_format:
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
                    downloaded_items.append(res)
                    downloaded_for_fmt += 1
                    converted_info = f" -> Converted: {Path(res['converted_file']).name}" if res.get("converted_file") else ""
                    print(f"   ✅ [{fmt_clean.upper()}] {res['file_name']} ({res['size']:,} bytes){converted_info}")
                    time.sleep(0.8)
        # Fallback to curated seeds if still below limit_per_format
        if downloaded_for_fmt < limit_per_format and topic_key_or_name in FAMOUS_TOPICS:
            topic_def = FAMOUS_TOPICS[topic_key_or_name]
            seeds = topic_def.curated_seeds.get(fmt_clean, [])
            for seed_url, seed_title in seeds:
                if downloaded_for_fmt >= limit_per_format:
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
                    downloaded_items.append(res)
                    downloaded_for_fmt += 1
                    converted_info = f" -> Converted: {Path(res['converted_file']).name}" if res.get("converted_file") else ""
                    print(f"   ✅ [CURATED {fmt_clean.upper()}] {res['file_name']} ({res['size']:,} bytes){converted_info}")
                    time.sleep(0.5)

        print(f"   📊 Tổng .{fmt_clean} tải thành công: {downloaded_for_fmt}/{limit_per_format}")

    # Write manifest
    manifest_data = {
        "topic_key": topic_slug,
        "topic_name": topic_display,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(downloaded_items),
        "documents": downloaded_items,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Đã lưu danh mục tài liệu vào: {manifest_path}")

    return manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone Document Crawler - Thu thập tài liệu doc, docx, pdf, txt, md theo chủ đề."
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Chủ đề cần crawl (tên chủ đề hoặc key trong 5 chủ đề famous).",
    )
    parser.add_argument(
        "--crawl-5-famous",
        action="store_true",
        help="Tự động thu thập toàn bộ 5 chủ đề nổi tiếng (famous) nhất.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=SUPPORTED_FORMATS,
        help=f"Danh sách các định dạng cần crawl (Mặc định: {', '.join(SUPPORTED_FORMATS)}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="Số lượng tài liệu mục tiêu cho mỗi định dạng (Mặc định: 2 file/định dạng).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(CURRENT_DIR / "output"),
        help="Thư mục gốc lưu trữ dữ liệu tải về (Mặc định: tools/crawler/output).",
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="Hiển thị danh sách 5 chủ đề nổi tiếng (famous) có sẵn.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Bật log chi tiết debug.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.list_topics:
        print("\n📚 DANH SÁCH 5 CHỦ ĐỀ NỔI TIẾNG (FAMOUS TOPICS):")
        print("-----------------------------------------------------------------")
        for key, item in FAMOUS_TOPICS.items():
            print(f"  • [{key}]: {item.name}")
            print(f"    Mô tả: {item.description}")
            print(f"    Từ khóa mẫu: {', '.join(item.search_keywords[:3])}\n")
        sys.exit(0)

    output_base_dir = Path(args.output_dir)

    if args.crawl_5_famous:
        print("\n🚀 KHỞI ĐỘNG CRAWL TOÀN BỘ 5 CHỦ ĐỀ NỔI TIẾNG")
        print(f"Số lượng mục tiêu: {args.limit} tệp / định dạng / chủ đề")
        print(f"Thư mục lưu trữ: {output_base_dir}\n")

        summary = {}
        for key in FAMOUS_TOPICS:
            manifest = crawl_single_topic(
                topic_key_or_name=key,
                formats=args.formats,
                limit_per_format=args.limit,
                output_base_dir=output_base_dir,
            )
            summary[key] = manifest["total_documents"]
            time.sleep(1.0)

        print("\n=======================================================")
        print("🎉 HOÀN THÀNH CRAWL 5 CHỦ ĐỀ!")
        print("=======================================================")
        for key, count in summary.items():
            print(f"  - {FAMOUS_TOPICS[key].name}: {count} tài liệu")
        print(f"📁 Kiểm tra dữ liệu tại: {output_base_dir}")
        sys.exit(0)

    if args.topic:
        crawl_single_topic(
            topic_key_or_name=args.topic,
            formats=args.formats,
            limit_per_format=args.limit,
            output_base_dir=output_base_dir,
        )
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
