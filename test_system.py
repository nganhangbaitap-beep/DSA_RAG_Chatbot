# -*- coding: utf-8 -*-
# test_system.py - File kiểm tra hệ thống RAG Hybrid (Local Embedding + Cloud Chat)

import os
import time
import sys
import shutil
from dotenv import load_dotenv
from config import CHROMA_PERSIST_DIR  # Import để quản lý dữ liệu kiểm tra

# 1. Nạp biến môi trường
load_dotenv()

def print_banner(text):
    print("\n" + "="*50)
    print(f"🧪 {text}")
    print("="*50)

def run_test():
    print_banner("KIỂM TRA HỆ THỐNG DSA CHATBOT (MÔ HÌNH HYBRID RAG)")

    # --- Bước 1: Kiểm tra API Key (Cho phần Cloud Chat) ---
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not gemini_key or "your_gemini" in gemini_key:
        print("❌ LỖI: Chưa cấu hình GEMINI_API_KEY trong file .env")
        return
    print(f"✅ Gemini API Key: {gemini_key[:10]}...")

    if not groq_key or "your_groq" in groq_key:
        print("⚠️ CẢNH BÁO: Chưa cấu hình GROQ_API_KEY. Hệ thống sẽ không có AI dự phòng!")
    else:
        print(f"✅ Groq API Key:   {groq_key[:10]}...")

    # Kiểm tra và Import thư viện
    try:
        from core.embedder import GeminiEmbedder
        from core.vector_store import VectorStore
        from core.rag_chain import RAGChain
        from langchain_core.documents import Document
        from core.chunker import split_documents
        
        # SDK mới cho phần hội thoại Cloud
        from google import genai
        from groq import Groq
    except ImportError as e:
        print(f"❌ LỖI: Thiếu thư viện hành nền. Hãy chạy: pip install google-genai groq sentence-transformers python-dotenv\nChi tiết: {e}")
        return

    # --- Bước 2: Kiểm tra kết nối Cloud Chat (Gemini) ---
    print("\n🌐 Kiểm tra kết nối Chat Cloud (Gemini API)...")
    try:
        client = genai.Client(api_key=gemini_key)
        model_name = 'gemini-flash-latest'
        response = client.models.generate_content(
            model=model_name,
            contents="Hãy nói 1 câu chào thật ngắn gọn"
        )
        print(f"✅ Gemini Cloud phản hồi ({model_name}): {response.text.strip()[:40]}...")
    except Exception as e:
        print(f"❌ LỖI kết nối Chat Gemini Cloud: {e}")
        return

    # --- Bước 2.5: Kiểm tra kết nối Cloud Chat Dự phòng (Groq) ---
    if groq_key and "your_groq" not in groq_key:
        print("\n⚡ Kiểm tra kết nối Chat Cloud Dự phòng (Groq API)...")
        try:
            groq_client = Groq(api_key=groq_key)
            groq_response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": "Hi"}],
                model="llama3-70b-8192",
            )
            print(f"✅ Groq Cloud phản hồi: {groq_response.choices[0].message.content.strip()[:40]}...")
        except Exception as e:
            print(f"⚠️ Cảnh báo kết nối Groq thất bại: {e}")

    # --- Bước 3: Kiểm tra Local Embedding Engine (Chạy Offline) ---
    print("\n🚀 Kiểm tra Local Embedding Engine (Chạy Offline trên thiết bị)...")
    print("💡 Mẹo: Nếu đây là lần đầu chạy, hệ thống sẽ tự động tải Model (~420MB) về máy. Vui lòng đợi...")
    try:
        start_time = time.time()
        embedder = GeminiEmbedder() # Thực chất chạy SentenceTransformer cục bộ bên dưới
        
        # Thực hiện trích xuất thử vector
        vec = embedder.embed_query("Cấu trúc dữ liệu Stack")
        duration = time.time() - start_time
        
        if vec and isinstance(vec, list):
            print(f"✅ Local Embedding OK! Kích thước Vector đạt chuẩn: {len(vec)} chiều (Xử lý trong {duration:.2f}s)")
        else:
            print("❌ LỖI: Không nhận được dữ liệu định dạng Vector hợp lệ.")
            return
    except Exception as e:
        print(f"❌ LỖI khởi tạo hoặc chạy Local Embedding: {e}")
        print("💡 GỢI Ý: Hãy chắc chắn bạn đã cài đặt thư viện: pip install sentence-transformers")
        return

    # --- Bước 4: Kiểm tra Vector DB & Search cục bộ ---
    print("\n📦 Kiểm tra Đọc/Ghi & Tìm kiếm trên Vector Database (ChromaDB)...")
    try:
        vs = VectorStore(embedder)
        
        # Tạo dữ liệu ảo để test tính năng tìm kiếm ngữ cảnh
        test_docs = [Document(page_content="Hàng đợi (Queue) hoạt động theo nguyên lý vào trước ra trước (FIFO).", metadata={"source":"he_thong_test.pdf"})]
        chunks = split_documents(test_docs)
        
        # Thêm vào DB
        vs.add_documents(chunks)
        
        # Tìm kiếm thử nghiệm
        results = vs.similarity_search("Nguyên lý FIFO là gì?", k=1)
        if results and "FIFO" in results[0].page_content:
            print(f"✅ Truy vấn ChromaDB thành công: \"{results[0].page_content[:50]}...\"")
        else:
            print("❌ LỖI: DB không trả về đúng kết quả ngữ cảnh mong đợi.")
            
    except Exception as e:
        print(f"⚠️ Cảnh báo lỗi vận hành Vector Store: {e}")
        print("💡 GỢI Ý: Nếu dính lỗi kích thước vector (Dimension), hãy xóa thư mục 'chroma_db' hiện tại đi rồi chạy lại file này.")

    print_banner("KIỂM TRA HOÀN TẤT - HỆ THỐNG HYBRID RAG SẴN SÀNG! HÃY CHẠY: streamlit run app.py")

if __name__ == "__main__":
    run_test()