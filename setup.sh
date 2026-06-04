#!/bin/bash
# setup.sh - Cài đặt tự động (Linux/macOS)

set -e  # Dừng nếu có lỗi

echo ""
echo "===================================================="
echo "  DSA RAG Chatbot - Cài đặt tự động (Linux/macOS)"
echo "===================================================="
echo ""

# Kiểm tra Python 3.10+
PYTHON_CMD=""
for cmd in python3.11 python3.10 python3 python; do
    if command -v $cmd &>/dev/null; then
        VER=$($cmd -c "import sys; print(sys.version_info >= (3,10))")
        if [ "$VER" = "True" ]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[LỖI] Cần Python 3.10 trở lên!"
    echo "      Ubuntu: sudo apt install python3.11"
    echo "      macOS:  brew install python@3.11"
    exit 1
fi
echo "[✓] Python: $($PYTHON_CMD --version)"

# Tạo virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/5] Tạo virtual environment..."
    $PYTHON_CMD -m venv .venv
else
    echo "[1/5] Virtual environment đã tồn tại"
fi

# Kích hoạt venv
echo "[2/5] Kích hoạt venv..."
source .venv/bin/activate

# Nâng cấp pip
echo "[3/5] Nâng cấp pip..."
pip install --upgrade pip -q

# Cài thư viện
echo "[4/5] Cài đặt thư viện (2-3 phút)..."
pip install -r requirements.txt -q
echo "[✓] Thư viện đã cài xong"

# Tạo file .env
echo "[5/5] Tạo file .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[✓] Đã tạo file .env"
    echo ""
    echo ">>> QUAN TRỌNG: Mở file .env và điền GEMINI_API_KEY <<<"
else
    echo "[✓] File .env đã tồn tại"
fi

# Tạo thư mục
mkdir -p data chroma_db

echo ""
echo "===================================================="
echo "  CÀI ĐẶT HOÀN TẤT!"
echo "===================================================="
echo ""
echo "Bước tiếp theo:"
echo "  1. nano .env   (điền GEMINI_API_KEY)"
echo "  2. python ingest.py --file data/tailieu.pdf"
echo "  3. streamlit run app.py"
echo ""

# Kiểm tra Tesseract (cho OCR)
if ! command -v tesseract &>/dev/null; then
    echo "⚠️  Tesseract chưa cài (cần cho PDF scan):"
    echo "   Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-vie"
    echo "   macOS:  brew install tesseract tesseract-lang"
fi
