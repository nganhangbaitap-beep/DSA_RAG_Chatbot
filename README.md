---
title: DSA RAG Chatbot
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---
# 🧠 DSA RAG Chatbot
> Trợ lý AI thông minh cho môn **Cấu Trúc Dữ Liệu và Giải Thuật**  
> Powered by **Gemini 1.5 Flash** + **ChromaDB** + **Streamlit**

---

## 📋 Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| 📄 PDF thường | Đọc slide, giáo trình có sẵn text |
| 🔍 PDF scan (OCR) | Đọc tài liệu scan bằng Tesseract |
| 📝 Word (.docx) | Đọc đề cương, bài giảng Word |
| 🌐 Website | Crawl tài liệu online |
| 🤖 Gemini 1.5 Flash | AI trả lời thông minh, miễn phí |
| 💾 ChromaDB | Lưu vector cục bộ, không cần server |
| 🔒 Bảo mật API | Key lưu trong `.env`, không lên GitHub |

---

## 🚀 Cài đặt nhanh

### Windows
```bash
git clone <repo-url>
cd dsa-rag-chatbot
setup.bat
```

### Linux / macOS
```bash
git clone <repo-url>
cd dsa-rag-chatbot
chmod +x setup.sh && ./setup.sh
```

### Thủ công (mọi hệ điều hành)
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt
cp .env.example .env
# Mở .env và điền GEMINI_API_KEY
```

---

## 🔑 Tạo Gemini API Key (miễn phí)

1. Truy cập **https://aistudio.google.com/app/apikey**
2. Đăng nhập Google → Nhấn **"Create API Key"**
3. Chọn project (hoặc tạo mới) → Copy key
4. Mở file `.env`:
   ```
   GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXX
   ```

> **Gemini 1.5 Flash miễn phí:** 15 req/phút, 1M token/ngày — rất đủ dùng!

---

## 🔒 Bảo vệ API Key — Không lộ lên GitHub

### Cách 1: File `.env` (đơn giản nhất)
```bash
# .env (KHÔNG commit, đã có trong .gitignore)
GEMINI_API_KEY=AIzaSy...

# .env.example (commit lên GitHub — không có key thật)
GEMINI_API_KEY=your_gemini_api_key_here
```

### Cách 2: Biến môi trường hệ thống
```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY = "AIzaSy..."

# Linux/macOS
export GEMINI_API_KEY="AIzaSy..."
```

### Cách 3: Kiểm tra trước khi push
```bash
# Cài git-secrets để tự động chặn
git secrets --install
git secrets --register-aws  # chặn pattern key lộ
```

### ⚠️ Nếu lỡ push key lên GitHub
1. **Thu hồi key ngay** tại Google AI Studio
2. Tạo key mới
3. Xóa key khỏi lịch sử: `git filter-branch` hoặc `BFG Repo Cleaner`

---

## 📚 Nạp Tài Liệu

```bash
# Nạp 1 file PDF
python ingest.py --file data/giao_trinh_dsa.pdf

# Nạp PDF scan (OCR)
python ingest.py --file data/scan.pdf --ocr

# Nạp file Word
python ingest.py --file data/bai_giang.docx

# Nạp toàn bộ thư mục
python ingest.py --dir data/

# Nạp website
python ingest.py --url https://vi.wikipedia.org/wiki/Cấu_trúc_dữ_liệu

# Xóa database cũ và nạp lại
python ingest.py --dir data/ --clear
```

---

## ▶️ Chạy Chatbot

```bash
streamlit run app.py
```
Mở trình duyệt: **http://localhost:8501**

---

## 🧪 Kiểm tra hệ thống

```bash
python test_system.py
```

---

## 📁 Cấu trúc thư mục

```
dsa-rag-chatbot/
│
├── 📄 app.py              # Giao diện Streamlit
├── 📄 ingest.py           # Script nạp tài liệu
├── 📄 config.py           # Cấu hình (đọc từ .env)
├── 📄 test_system.py      # Kiểm tra hệ thống
│
├── 📂 loaders/            # Đọc tài liệu
│   ├── pdf_loader.py      # PDF thường (pdfplumber)
│   ├── ocr_loader.py      # PDF scan (Tesseract)
│   ├── word_loader.py     # Word (python-docx)
│   └── web_loader.py      # Website (BeautifulSoup)
│
├── 📂 core/               # Lõi RAG
│   ├── chunker.py         # Chia nhỏ văn bản
│   ├── embedder.py        # Gemini Embeddings
│   ├── vector_store.py    # ChromaDB
│   └── rag_chain.py       # Pipeline RAG + Gemini
│
├── 📂 data/               # Tài liệu upload (gitignored)
├── 📂 chroma_db/          # Vector database (gitignored)
│
├── 📄 .env                # API keys (gitignored ⚠️)
├── 📄 .env.example        # Template .env (commit OK)
├── 📄 .gitignore          # Bảo vệ key & data
├── 📄 requirements.txt    # Thư viện Python
├── 📄 setup.bat           # Cài đặt Windows
└── 📄 setup.sh            # Cài đặt Linux/macOS
```

---

## 🤖 Gemini 1.5 Flash phù hợp cho DSA không?

**Trả lời: RẤT PHÙ HỢP** vì:

| Tiêu chí | Gemini 1.5 Flash |
|----------|-----------------|
| Context window | **1 triệu token** — đọc cả giáo trình dày |
| Tiếng Việt | Hiểu và trả lời tiếng Việt tốt |
| Code Python | Sinh code chính xác, có comment |
| Thuật toán | Giải thích DSA rõ ràng, có ví dụ |
| Tốc độ | Nhanh (~1-2 giây/câu trả lời) |
| Chi phí | **Miễn phí** tier rất rộng |

---

## ❓ Câu hỏi thường gặp

**Q: PDF scan không đọc được?**  
A: Cài Tesseract: `sudo apt install tesseract-ocr tesseract-ocr-vie`

**Q: Lỗi "GEMINI_API_KEY not found"?**  
A: Kiểm tra file `.env` có tồn tại và có key đúng định dạng

**Q: Chromadb lỗi khi thêm documents?**  
A: Xóa thư mục `chroma_db/` và nạp lại

**Q: Muốn dùng model khác?**  
A: Sửa trong `.env`: `GEMINI_MODEL=gemini-1.5-pro`
