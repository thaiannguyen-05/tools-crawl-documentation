# 🕷️ Document Crawler & RAG Training Data Pipeline

Bộ công cụ độc lập (standalone) chạy trên CLI dùng để:
1. **Thu thập tài liệu đa định dạng** (`.pdf`, `.docx`, `.doc`, `.txt`, `.md`) tự động theo chủ đề.
2. **Chạy qua RAG Pipeline**: Bóc tách nội dung, chia chunk theo ngữ cảnh, vector hóa bằng **PhoBERT-large** (1024 chiều) và gộp (aggregate) các vector chunk thành **1 vector đại diện duy nhất** cho mỗi tài liệu.
3. **Gắn nhãn thể loại & Xuất Training Data**: Lưu dưới dạng bảng **`training_data.csv`** (và `training_data.pkl`) chuẩn đầu vào để huấn luyện mô hình phân loại (Classification).

> [!NOTE]
> Bộ công cụ này được thiết kế **hoàn toàn độc lập** và có thể copy/git pull sang bất kỳ máy tính nào chạy mà không cần phụ thuộc vào toàn bộ hệ thống lớn.

---

## 🔄 Kiến Trúc Luồng Hoạt Động

```text
[1. Thu thập dữ liệu theo Chủ đề (Label)]
       │ (Không quan trọng loại file gốc là PDF, DOCX, DOC, TXT hay MD)
       ├── ai_tech/            -> Gán Label: 'ai_tech'
       ├── economy_finance/    -> Gán Label: 'economy_finance'
       ├── health_medicine/    -> Gán Label: 'health_medicine'
       └── ...
       │
[2. RAG Pipeline (Bóc tách & Chunking)]
       │
       ├── text_extractor.py   -> Bóc tách text, headings, sections
       ├── chunker.py          -> Tách câu, trượt overlap 64 ký tự
       ├── tokenizer.py        -> Tách từ tiếng Việt chuẩn PhoBERT BPE
       └── model/phoBert       -> PhoBERT-large sinh vector 1024 chiều từng chunk
       │
[3. Aggregate các vector chunk]
       │
       └── aggregate_chunk_vectors(chunks, method='mean') -> 1 vector / tài liệu
       │
[4. Xuất dữ liệu huấn luyện đã gắn nhãn]
       │
       ├── output/training_data.csv          (vector, label, file_name)
       ├── output/training_data.pkl          (dict[label, list[vector]])
       └── output/training_data_summary.json (Báo cáo thống kê)
```

---

## 🚀 Cài Đặt Môi Trường

Yêu cầu: **Python 3.10+**

```bash
# 1. Tạo môi trường ảo (Khuyên dùng)
python3 -m venv venv

# Kích hoạt môi trường ảo:
# Trên Linux/macOS:
source venv/bin/activate
# Trên Windows:
venv\Scripts\activate

# 2. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

---

## 💻 Hướng Dẫn Sử Dụng Chi Tiết

Công cụ hỗ trợ linh hoạt 2 chế độ: **Giao diện tương tác CLI (Interactive Wizard)** và **Tham số dòng lệnh (CLI Flags)**.

---

### 🌟 Chế độ 1: Giao diện tương tác trực tiếp (Khuyên dùng)

Chỉ cần gõ lệnh (không cần nhớ cờ tham số):
```bash
python crawl.py
```
*(hoặc `python crawl.py -i`)*

Màn hình tương tác sẽ xuất hiện trên terminal:
```text
=================================================================
🕷️  CÔNG CỤ CRAWLER TÀI LIỆU ĐA ĐỊNH DẠNG (CLI INTERACTIVE)
=================================================================
Danh sách 5 chủ đề nổi tiếng (Famous Topics):
  [1] Trí tuệ nhân tạo & Công nghệ thông tin (ai_tech)
  [2] Kinh tế & Tài chính (economy_finance)
  [3] Y tế & Sức khỏe (health_medicine)
  [4] Pháp luật & Quản lý (law_governance)
  [5] Giáo dục & Môi trường (education_environment)

Chọn chế độ hoạt động:
  [1] Chọn từng chủ đề cụ thể và nhập số lượng bản ghi riêng
  [2] Crawl toàn bộ 5 chủ đề nổi tiếng (Nhập số lượng cho mỗi chủ đề)
  [3] Nhập một chủ đề tùy chỉnh mới
  [0] Thoát
-----------------------------------------------------------------
```

* **Chọn `[1]`**: Cho phép chọn các chủ đề cụ thể (ví dụ: `1, 3` hoặc `1-3`). Sau đó nhập số lượng bản ghi riêng cho từng chủ đề:
  * 👉 *Số lượng bản ghi cho 'Trí tuệ nhân tạo & CNTT':* `10`
  * 👉 *Số lượng bản ghi cho 'Kinh tế & Tài chính':* `5`
* **Chọn `[2]`**: Tải cả 5 chủ đề với số lượng chung (ví dụ: mỗi chủ đề 5 bản ghi) hoặc tùy chỉnh số lượng từng chủ đề.
* Sau khi crawl xong, chương trình sẽ tự động hỏi:
  * 👉 *Bạn có muốn chạy Pipeline xử lý vector và xuất training_data.csv ngay bây giờ? [Y/n]:* ➔ Bấm `Enter` để chạy luôn!

---

### ⚡ Chế độ 2: Dòng lệnh CLI Flags (Tự động hóa)

#### 1. Vừa crawl vừa chạy Pipeline xuất luôn file `training_data.csv` (`--process` hoặc `-p`)
```bash
# Crawl 5 chủ đề, mỗi chủ đề lấy 5 bản ghi và xuất training_data.csv:
python crawl.py --crawl-5-famous --count 5 --process

# Đặt số lượng bản ghi riêng biệt cho từng chủ đề:
python crawl.py --topic-counts "ai_tech=10,economy_finance=5,health_medicine=8" --process

# Chỉ crawl 1 chủ đề với 12 bản ghi:
python crawl.py --topic ai_tech --count 12 --process
```

#### 2. Chỉ crawl tài liệu về máy (không chạy vector hóa)
```bash
# Crawl 5 chủ đề, mỗi chủ đề 3 bản ghi:
python crawl.py --crawl-5-famous --count 3

# Crawl theo từ khóa bất kỳ:
python crawl.py --topic "Năng lượng mặt trời và pin lithium" --count 5
```

#### 3. Giới hạn định dạng file cần tải (`--formats`)
```bash
# Chỉ tải PDF và DOCX:
python crawl.py --topic ai_tech --count 6 --formats pdf docx
```

#### 4. Xem danh sách 5 chủ đề mẫu có sẵn
```bash
python crawl.py --list-topics
```

---

### 🧠 Chế độ 3: Chạy Pipeline xử lý Training Data riêng biệt (`processor.py`)

Nếu bạn đã có các tệp tài liệu trong thư mục `./output/` và muốn chạy lại Pipeline (Bóc tách ➔ Cắt chunk ➔ Vector hóa ➔ Aggregate ➔ Gán nhãn):

```bash
# Chạy pipeline tạo cả training_data.csv và training_data.pkl:
python processor.py --input-dir ./output --output-file ./output/training_data.pkl

# Tùy chọn phương pháp aggregate ('mean', 'max', 'weighted'):
python processor.py --method mean

# Chế độ kiểm thử nhanh (dùng mock vector 32 chiều để test logic):
python processor.py --fast-test
```

---

## 📊 Định Dạng Dữ Liệu Huấn Luyện (Training Data Output)

### 1. File CSV: `output/training_data.csv`

File có định dạng bảng chuẩn, mỗi hàng là một tài liệu:

| vector | label | file_name |
| :--- | :--- | :--- |
| `[0.1671, 0.1489, -0.052, ...]` | `ai_tech` | `Tong_Quan_Ve_Tri_Tue_Nhan_Tao.pdf` |
| `[0.1610, 0.1591, 0.083, ...]` | `ai_tech` | `Huong_dan_NLP.md` |
| `[0.1534, 0.1245, -0.012, ...]` | `economy_finance` | `Nghi_dinh_tai_chinh.docx` |
| `[0.1450, 0.1620, 0.045, ...]` | `health_medicine` | `Y_hoc_cong_dong.txt` |

#### Đọc và xử lý bằng Pandas:
```python
import pandas as pd
import json

df = pd.read_csv("output/training_data.csv")
print("Tổng số bản ghi:", len(df))
print(df["label"].value_counts())  # Đếm số tài liệu theo từng nhãn

# Lấy vector của dòng đầu tiên
first_vector = json.loads(df["vector"].iloc[0])
print("Kích thước vector:", len(first_vector))
```

---

### 2. File Pickle: `output/training_data.pkl`
Lưu dưới dạng dictionary Python:
```python
{
    "ai_tech":          [doc_vector_1, doc_vector_2, ...],
    "economy_finance":  [doc_vector_1, doc_vector_2, ...],
    "health_medicine":  [doc_vector_1, doc_vector_2, ...],
}
```

---

## 🎯 Mục Đích Dữ Liệu Đầu Ra

Toàn bộ file **`output/training_data.csv`** (hoặc `training_data.pkl`) được tạo ra chính là tập dữ liệu huấn luyện (Training Dataset) đã được gắn nhãn thể loại, sẵn sàng để:
1. Đưa sang bên module KNN Classifier (`apps/knn`) huấn luyện mô hình phân loại tài liệu.
2. Dùng cho bất kỳ mô hình Machine Learning / Phân cụm / Tìm kiếm ngữ nghĩa nào khác.

---

## 📑 Bảng Tra Cứu Tham Số Dòng Lệnh (`crawl.py`)

| Tham số | Viết tắt | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- | :--- |
| `--interactive` | `-i` | Bật giao diện tương tác CLI | `python crawl.py -i` |
| `--crawl-5-famous` | | Crawl toàn bộ 5 chủ đề nổi tiếng | `python crawl.py --crawl-5-famous` |
| `--topic` | | Chỉ định 1 chủ đề cần crawl | `python crawl.py --topic ai_tech` |
| `--count` | `-c` | Số lượng bản ghi cho chủ đề | `python crawl.py --count 10` |
| `--topic-counts` | | Đặt số bản ghi riêng cho từng chủ đề | `python crawl.py --topic-counts "ai_tech=10,economy_finance=5"` |
| `--process` | `-p` | Tự động chạy Pipeline tạo `training_data.csv` | `python crawl.py --crawl-5-famous -c 5 -p` |
| `--formats` | | Giới hạn các định dạng cần tải | `python crawl.py --formats pdf docx txt` |
| `--output-dir` | | Thư mục lưu dữ liệu xuất ra | `python crawl.py --output-dir ./output` |
| `--list-topics` | | Xem danh sách 5 chủ đề mẫu | `python crawl.py --list-topics` |
| `--verbose` | `-v` | Bật log debug chi tiết | `python crawl.py -v` |
