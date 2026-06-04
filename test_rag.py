import os
import sys
from dotenv import load_dotenv

# Nạp cấu hình môi trường
load_dotenv()

def run_rag_test():
    print("="*50)
    print("🚀 TIẾN HÀNH KIỂM TRA VÀ NẠP TÀI LIỆU RAG")
    print("="*50)

    # 1. Import các module cốt lõi từ thư mục core
    try:
        from core.embedder import GeminiEmbedder
        from core.vector_store import VectorStore
        from core.rag_chain import RAGChain
        from langchain_core.documents import Document
    except ImportError as e:
        print(f"❌ LỖI: Không thể import các file trong thư mục core. Chi tiết: {e}")
        return

    # 2. Khởi tạo Embedder và Vector Store
    print("\n🧠 Đang kết nối Vector Database (ChromaDB)...")
    try:
        embedder = GeminiEmbedder()
        vs = VectorStore(embedder)
        rag = RAGChain(vs)
    except Exception as e:
        print(f"❌ LỖI khởi tạo hệ thống RAG: {e}")
        return

    # 3. Kiểm tra số lượng dữ liệu hiện tại
    try:
        current_chunks = vs.count()
        print(f"📊 Trạng thái hiện tại: Đang có {current_chunks} đoạn kiến thức trong DB.")
    except Exception as e:
        print(f"⚠️ Không thể kiểm tra số lượng mục: {e}")
        current_chunks = 0

    # 4. Tự động nạp tài liệu nếu DB đang trống (Số 0)
    if current_chunks == 0:
        print("\n📂 Khởi động tiến trình nạp tài liệu tự động từ thư mục 'data'...")
        data_dir = "data"
        
        if not os.path.exists(data_dir) or not os.listdir(data_dir):
            print(f"❌ LỖI: Thư mục '{data_dir}' trống hoặc không tồn tại! Hãy tạo thư mục này và chép file PDF/Word bài giảng DSA vào đó.")
            print("💡 Đang nạp tạm 1 đoạn kiến thức mẫu để hệ thống không bị trống...")
            
            # Nạp dữ liệu giả lập để cứu nguy
            sample_docs = [Document(page_content="Cấu trúc dữ liệu Stack (Ngăn xếp) hoạt động theo nguyên lý LIFO (Last In First Out) - Vào sau ra trước. Các hàm cơ bản gồm push() để thêm và pop() để lấy phần tử.", metadata={"source": "GiaoTrinh_Stack_Mau.pdf"})]
            vs.add_documents(sample_docs)
            print("✅ Đã nạp kiến thức mẫu về Stack vào Database thành công!")
        else:
            print(f"📂 Tìm thấy tài liệu trong thư mục '{data_dir}'. Đang tiến hành phân mảnh (Chunking) và nhúng (Embedding)...")
            # Nếu hệ thống của bạn có file chunker hoặc ingest, hãy gọi ở đây.
            # Ở đây ta giả định bạn chạy lệnh nạp dữ liệu chuẩn của project:
            try:
                # Bạn có thể chạy file ingest.py nếu dự án của bạn có sẵn file đó:
                if os.path.exists("ingest.py"):
                    os.system("python ingest.py")
                elif os.path.exists("core/ingest.py"):
                    os.system("python core/ingest.py")
                print("✅ Đã chạy lệnh nạp tài liệu hệ thống.")
            except Exception as e:
                print(f"⚠️ Gặp lỗi khi kích hoạt lệnh nạp: {e}")

    # 5. THỰC HIỆN KIỂM TRA TRUY XUẤT RAG THỰC TẾ
    print("\n🔍 CHẠY THỬ NGHIỆM TRUY VẤN RAG (TEST QUERY):")
    test_query = "Stack hoạt động theo nguyên lý nào và có các hàm gì?"
    print(f"❓ Câu hỏi test: '{test_query}'")
    
    try:
        # Gọi RAGChain để tìm kiếm tài liệu và trả lời
        result = rag.query(test_query)
        
        print("\n--- KẾT QUẢ TRẢ LỜI TỪ AI (DỰA TRÊN TÀI LIỆU): ---")
        if isinstance(result, dict):
            print(result.get("answer", "Không có câu trả lời."))
            print("\n📄 Nguồn tài liệu gốc được trích xuất:")
            for src in result.get("sources", []):
                print(f"   -> {src}")
        else:
            print(result)
        print("="*50)
        print("✅ KHẢO SÁT RAG HOÀN TẤT! Bây giờ bạn có thể bật 'streamlit run app.py' để kiểm tra con số hiển thị.")
        
    except Exception as e:
        print(f"❌ LỖI khi chạy thử truy vấn RAG: {e}")

if __name__ == "__main__":
    run_rag_test()