# -*- coding: utf-8 -*-
# core/embedder.py

import os
from typing import List
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

class GeminiEmbedder:
    """
    Hệ thống Local Embedding chạy OFFLINE hoàn toàn.
    Giữ lại tên lớp 'GeminiEmbedder' nhằm đảm bảo tính tương thích tuyệt đối 100%
    với toàn bộ dự án (ingest.py, vector_store.py, app.py) mà không cần đổi lệnh import.
    """
    def __init__(self):
        print(f"🚀 Khởi tạo Local Embedding Engine với model: {EMBEDDING_MODEL}...")
        # Ở lần chạy đầu tiên, hệ thống tự động tải mô hình này về máy (~420MB) để lưu vào cache.
        # Từ các lần sau trở đi, mô hình chạy hoàn toàn Offline, không phụ thuộc internet hay API Key.
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        print("  [OK] Local Embedding đã sẵn sàng vận hành.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Mã hóa hàng loạt danh sách các chunk văn bản khi chạy nạp tài liệu (ingest)."""
        if not texts:
            return []
        
        # Chạy cục bộ bằng phần cứng máy bạn (CPU/GPU) nên xử lý cực kì nhanh.
        # Không cần cơ chế ngủ (sleep), lặp lại (retry) hay lưu checkpoint né lỗi 429 như Cloud API.
        embeddings = self.model.encode(texts, batch_size=64, show_progress_bar=False)
        
        # Chuyển đổi định dạng mảng numpy của sentence-transformers thành list[float] để ChromaDB nhận diện tốt
        return [list(map(float, vec)) for vec in embeddings]

    def embed_query(self, text: str) -> List[float]:
        """Mã hóa câu hỏi/câu truy vấn của người dùng khi chat để tìm kiếm ngữ cảnh."""
        if not text:
            return []
        embedding = self.model.encode(text)
        return list(map(float, embedding))

    def get_langchain_embedder(self):
        """Duck-typing: Trả về chính thực thể lớp này để làm embedding_function cho ChromaDB."""
        return self