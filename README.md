# 🕷️ Standalone Document Crawler Tool

Công cụ độc lập (standalone) dùng để tìm kiếm và thu thập tự động các tài liệu đa định dạng (`.pdf`, `.docx`, `.doc`, `.txt`, `.md`) theo chủ đề, ưu tiên tài liệu tiếng Việt chất lượng cao.

Công cụ này được thiết kế **hoàn toàn khép kín**, bạn có thể sao chép nguyên thư mục `tools/crawler` sang bất kỳ máy tính nào (Windows, Linux, macOS) và chạy độc lập mà không cần toàn bộ repository dự án.

---

## 🌟 Tính Năng Nổi Bật

1. **Đa nguồn thu thập**:
   - **Tài liệu PDF, DOCX, DOC**: Tự động tìm kiếm qua DuckDuckGo HTML với bộ lọc `filetype:` chuyên sâu.
   - **Tài liệu Text (.txt)**: Kết nối Wikipedia tiếng Việt API trích xuất bài viết chi tiết, chuẩn cấu trúc.
   - **Tài liệu Markdown (.md)**: Tự động khai thác tài liệu, sách và README tiếng Việt chất lượng cao từ GitHub.
2. **5 Chủ đề nổi tiếng tích hợp sẵn (`--crawl-5-famous`)**:
   - `ai_tech`: Trí tuệ nhân tạo & Công nghệ thông tin
   - `economy_finance`: Kinh tế & Tài chính
   - `health_medicine`: Y tế & Sức khỏe
   - `law_governance`: Pháp luật & Quản lý
   - `education_environment`: Giáo dục & Môi trường
3. **Xử lý tệp `.doc` cũ thông minh**:
   - Nếu tải về tệp `.doc` (Word 97-2003 OLE binary), công cụ tự động trích xuất nội dung và sinh ra tệp phụ trợ `.extracted.txt` tương ứng để tương thích 100% với pipeline RAG/KNN của hệ thống (tránh lỗi `UnsupportedFileError`).
4. **Quản lý Manifest & Checksum**:
   - Mỗi chủ đề sinh ra một file `manifest.json` ghi lại URL gốc, SHA-256, dung lượng, thời gian tải, và tình trạng chuyển đổi.

---

## 🚀 Hướng Dẫn Cài Đặt Khi Mang Sang Máy Khác

### Bước 1: Chuẩn bị môi trường Python (Python 3.10+)

```bash
# Tạo môi trường ảo
python3 -m venv venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source venv/bin/activate
# Trên Windows:
venv\Scripts\activate
```

### Bước 2: Cài đặt thư viện phụ thuộc

```bash
pip install -r requirements.txt
```

---

## 💻 Hướng Dẫn Sử Dụng

### 1. Xem danh sách 5 chủ đề nổi tiếng có sẵn
```bash
python crawl.py --list-topics
```

### 2. Thu thập trọn gói toàn bộ 5 chủ đề nổi tiếng
```bash
# Thu thập 5 chủ đề, mỗi định dạng tải 2 tệp (khoảng 10 tệp/chủ đề = 50 tệp)
python crawl.py --crawl-5-famous --limit 2

# Hoặc tăng số lượng lên 5 tệp / định dạng
python crawl.py --crawl-5-famous --limit 5
```

### 3. Thu thập theo một chủ đề cụ thể
```bash
# Dùng mã chủ đề có sẵn (ví dụ: ai_tech)
python crawl.py --topic ai_tech --limit 3

# Hoặc dùng từ khóa tùy ý
python crawl.py --topic "Năng lượng mặt trời và pin lưu trữ" --limit 2
```

### 4. Giới hạn định dạng tài liệu cần crawl
```bash
# Chỉ tải PDF và DOCX
python crawl.py --topic "Thị trường tài chính" --formats pdf docx --limit 5

# Chỉ tải Markdown và Text
python crawl.py --topic ai_tech --formats md txt --limit 3
```

### 5. Tùy chỉnh thư mục xuất dữ liệu
```bash
python crawl.py --topic ai_tech --output-dir /duong_dan_tuy_y/dataset
```

---

## 📂 Cấu Trúc Thư Mục Xuất Bản

```
output/
├── ai_tech/
│   ├── manifest.json
│   ├── Tong_Quan_Ve_Tri_Tue_Nhan_Tao.pdf
│   ├── De_cuong_mon_hoc_AI.docx
│   ├── Gioi_thieu_hoc_may.extracted.txt
│   ├── Gioi_thieu_hoc_may.doc
│   ├── Tri_tue_nhan_tao.txt
│   └── Huong_dan_PhoBERT.md
├── economy_finance/
│   ├── manifest.json
│   └── ...
└── ...
```

Mỗi thư mục con chứa các file văn bản đã được kiểm tra tính hợp lệ về định dạng (magic bytes header) và sẵn sàng đưa vào pipeline xử lý vector của `apps/knn/file_process`.
