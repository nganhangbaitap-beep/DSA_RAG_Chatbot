# config.py - Cấu hình toàn bộ dự án (Mô hình Hybrid: Local RAG + Cloud Chat)

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# API Configuration for LLM Chat (Giữ nguyên Cloud)
# ============================================
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL",   "gemini-flash-latest")

GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ============================================
# Vector Store — ChromaDB
# ============================================
CHROMA_PERSIST_DIR     = os.getenv("CHROMA_PERSIST_DIR",     "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "dsa_knowledge")

# ============================================
# Local Embedding Configuration (Chuyển sang Local Offline)
# ============================================
# Sử dụng model đa ngôn ngữ siêu nhẹ, tối ưu cho cả tiếng Việt và tiếng Anh chạy trên CPU/GPU local
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ============================================
# Text Chunking
# ============================================
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE",    "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# ============================================
# RAG Settings
# ============================================
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "8"))
TEMPERATURE   = float(os.getenv("TEMPERATURE", "0.3"))
MAX_TOKENS    = int(os.getenv("MAX_TOKENS",    "2048"))

# ============================================
# System Prompt
# ============================================
SYSTEM_PROMPT = """[BẢN CHẤT]: Bạn là trợ lý học tập chuyên ngành Cấu trúc dữ liệu và Giải thuật (DSA), hỗ trợ sinh viên học tập và lập trình.

[PHẠM VI ĐƯỢC PHÉP]:
- Giải thích lý thuyết DSA: mảng, danh sách liên kết, cây, đồ thị, ngăn xếp, hàng đợi, sắp xếp, tìm kiếm...trong tài liệu cung cấp
- Kiểm tra, debug, sửa lỗi code của sinh viên bằng bất kỳ ngôn ngữ nào (C++, Python, Java, C...)
- Phân tích độ phức tạp thuật toán O(n), O(log n)...
- Viết code minh họa thuật toán khi được yêu cầu
- Giải thích lỗi cú pháp, lỗi logic, lỗi kiểu dữ liệu trong code

[PHẠM VỊ KHÔNG ĐƯỢC]: Không trả lời về thời tiết, đời tư, chính trị, hoặc chủ đề hoàn toàn không liên quan đến học tập lập trình.

[KHI SINH VIÊN PASTE CODE]:
1. Đọc và hiểu toàn bộ đoạn code
2. Chỉ ra lỗi cụ thể (cú pháp, logic, kiểu dữ liệu, edge case...)
3. Đưa ra code đã sửa hoàn chỉnh
4. Giải thích ngắn gọn lý do sửa từng chỗ

[NGÔN NGỮ]: Câu hỏi tiếng Việt → trả lời tiếng Việt..."""
# Thêm vào cuối file config.py

# Tên chính xác của File Google Sheets lưu trên Google Drive của bạn
GOOGLE_SHEET_NAME = "Quan_Ly_Lop_DSA"

# Tên các Tab bên trong file Sheets
TAB_DANH_SACH = "DanhSachLop"
TAB_LICH_SU = "LichSuDangXuat"