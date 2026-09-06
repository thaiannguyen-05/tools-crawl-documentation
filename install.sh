#!/usr/bin/env bash
# ==============================================================================
# Script Cài Đặt Toàn Bộ Dependencies Cho Tools Scrawl Documentation & RAG Pipeline
# Hỗ trợ: Linux / macOS
# ==============================================================================
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}🚀 BẮT ĐẦU CÀI ĐẶT MÔI TRƯỜNG & DEPENDENCIES${NC}"
echo -e "${BLUE}=================================================================${NC}"

# 1. Tìm Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo -e "${RED}❌ Lỗi: Không tìm thấy Python! Vui lòng cài đặt Python >= 3.10.${NC}"
    exit 1
fi

PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo -e "${RED}❌ Phiên bản Python hiện tại ($PY_VER) không được hỗ trợ. Cần Python >= 3.10.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Đã tìm thấy Python: $PYTHON_BIN (Phiên bản $PY_VER)${NC}"

# 2. Khởi tạo Virtual Environment (.venv) nếu chưa có
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}📦 Đang tạo virtual environment tại './$VENV_DIR'...${NC}"
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Đã tạo virtual environment thành công.${NC}"
else
    echo -e "${YELLOW}ℹ️  Virtual environment './$VENV_DIR' đã tồn tại.${NC}"
fi

# 3. Kích hoạt Virtual Environment
echo -e "${BLUE}🔌 Đang kích hoạt virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
VENV_PYTHON=$(which python)
echo -e "${GREEN}✅ Python đang dùng: $VENV_PYTHON${NC}"

# 4. Cập nhật pip & build tools
echo -e "${BLUE}🔄 Đang nâng cấp pip, setuptools, wheel...${NC}"
pip install --upgrade pip setuptools wheel --quiet

# 5. Cài đặt các gói từ requirements.txt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

if [ -f "$REQ_FILE" ]; then
    echo -e "${BLUE}📥 Đang cài đặt thư viện từ requirements.txt... (Có thể mất vài phút)${NC}"
    pip install -r "$REQ_FILE"
else
    echo -e "${RED}❌ Không tìm thấy file $REQ_FILE!${NC}"
    exit 1
fi

# 6. Kiểm tra các thư viện cốt lõi (Healthcheck)
echo ""
echo -e "${BLUE}🔍 Đang kiểm tra import các thư viện cốt lõi...${NC}"
python -c "
import sys
libs = [
    ('httpx', 'Crawl HTTP/Web'),
    ('bs4', 'HTML Parser'),
    ('docx', 'Word DOCX Reader'),
    ('pypdf', 'PDF Reader'),
    ('pdfplumber', 'PDF Plumber'),
    ('markdown_it', 'Markdown Parser'),
    ('numpy', 'Vector Processing'),
    ('torch', 'PyTorch Tensor Engine'),
    ('transformers', 'HuggingFace Transformers (PhoBERT)'),
    ('pandas', 'Dataset CSV Handler')
]

all_ok = True
for mod, desc in libs:
    try:
        __import__(mod)
        print(f'  ✅ {mod:<15} ({desc}): OK')
    except ImportError as e:
        print(f'  ❌ {mod:<15} ({desc}): THIẾU ({e})')
        all_ok = False

if not all_ok:
    sys.exit(1)
"

echo ""
echo -e "${GREEN}=================================================================${NC}"
echo -e "${GREEN}🎉 CÀI ĐẶT HOÀN TẤT THÀNH CÔNG!${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo -e "Để bắt đầu làm việc, bạn chỉ cần gõ lệnh:"
echo -e "   ${YELLOW}source .venv/bin/activate${NC}"
echo ""
echo -e "Sau đó chạy công cụ:"
echo -e "   ${YELLOW}python crawl.py -i${NC}                   # Giao diện tương tác CLI"
echo -e "   ${YELLOW}python crawl.py --crawl-5-famous -p${NC}  # Crawl 5 chủ đề & xuất CSV ngay"
echo -e "${GREEN}=================================================================${NC}"
