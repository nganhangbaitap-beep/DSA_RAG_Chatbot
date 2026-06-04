# -*- coding: utf-8 -*-
# core/vector_store.py

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from config import CHROMA_PERSIST_DIR  # Tái sử dụng đường dẫn thư mục lưu trữ từ cấu hình

# Đường dẫn lưu trữ DB thủ công bằng JSON
DB_FILEPATH = Path(CHROMA_PERSIST_DIR) / "pure_vector_store.json"


class VectorStore:
    def __init__(self, embedder):
        """
        Embedder: Thực thể lớp GeminiEmbedder (có phương thức embed_documents và embed_query)
        """
        self.embedder = embedder
        self.vectors: Dict[str, Dict[str, Any]] = {}       # id -> {text, embedding, metadata}
        self.hash_index: Dict[str, str] = {}               # content_hash -> id
        
        # Tự động nạp dữ liệu cũ từ ổ cứng nếu có sẵn
        self._load_from_disk()

    def _hash_text(self, text: str) -> str:
        """Tạo mã băm SHA256 cố định đại diện cho nội dung text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def _save_to_disk(self):
        """Lưu trữ bền vững toàn bộ dữ liệu từ RAM xuống ổ cứng dạng JSON."""
        DB_FILEPATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "vectors": self.vectors,
            "hash_index": self.hash_index
        }
        with open(DB_FILEPATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _load_from_disk(self):
        """Đọc lại dữ liệu đã lưu từ ổ cứng lên RAM khi khởi tạo hệ thống."""
        if DB_FILEPATH.exists():
            try:
                with open(DB_FILEPATH, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    self.vectors = payload.get("vectors", {})
                    self.hash_index = payload.get("hash_index", {})
                if len(self.vectors) > 0:
                    print(f"  [OK] Đã nạp thành công {len(self.vectors)} chunks từ cơ sở dữ liệu gốc.")
            except Exception as e:
                print(f"  [⚠️ Cảnh báo] Không thể đọc file DB cũ, khởi tạo DB trống. Lỗi: {e}")

    def add_documents(self, chunks: List[Document]) -> int:
        """
        Giao diện tương thích hoàn toàn với ingest.py (Nhận vào List[Document]).
        Tự động bóc tách chuỗi, băm dữ liệu lọc trùng, tạo embedding và lưu xuống đĩa.
        """
        if not chunks:
            return 0

        # Bóc tách cấu trúc Document của LangChain ra thành mảng thô như logic của bạn
        texts = [doc.page_content for doc in chunks]
        metadatas = [doc.metadata for doc in chunks]

        # Thực thi logic thêm dữ liệu tối ưu của bạn
        ids = self.add(texts, metadatas)
        
        # Đếm xem thực tế có bao nhiêu ID mới được sinh ra (không trùng, không lỗi)
        # Vì nếu trùng lịch sử, ids[idx] vẫn có giá trị nhưng không ghi mới vào self.vectors
        return len([i for i in ids if i is not None])

    def add(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Optional[str]]:
        """
        Logic lọc trùng tuyệt đối (Intra-batch & History) chuẩn xác của bạn.
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]

        assert len(texts) == len(metadatas), "Độ dài texts và metadatas phải khớp nhau!"

        ids: List[Optional[str]] = [None] * len(texts)
        new_texts = []
        new_indices = []
        batch_seen_hashes: Dict[str, str] = {}

        # Cache toàn bộ mã băm chuỗi đầu vào để tối ưu CPU
        hashes = [self._hash_text(t) for t in texts]

        # === BƯỚC 1: LỌC TRÙNG TUYỆT ĐỐI ===
        for i, (text, content_hash) in enumerate(zip(texts, hashes)):
            # 1. Đã tồn tại trong database từ trước (Lọc trùng lịch sử)
            if content_hash in self.hash_index:
                ids[i] = self.hash_index[content_hash]

            # 2. Bị trùng lặp ngay trong lô dữ liệu hiện tại
            elif content_hash in batch_seen_hashes:
                ids[i] = batch_seen_hashes[content_hash]

            # 3. Văn bản mới hoàn toàn
            else:
                doc_id = content_hash  # Dùng trực tiếp hash làm ID duy nhất
                new_texts.append(text)
                new_indices.append(i)
                batch_seen_hashes[content_hash] = doc_id

        # === BƯỚC 2: CHỈ EMBED CÁC CHUNK CHƯA TỪNG XUẤT HIỆN ===
        if new_texts:
            embeddings = self.embedder.embed_documents(new_texts)

            if len(embeddings) != len(new_texts):
                raise ValueError("Độ dài danh sách Vector trả về không khớp với số lượng chuỗi gửi đi!")

            for idx, text, emb in zip(new_indices, new_texts, embeddings):
                if emb is None or len(emb) == 0:
                    continue

                content_hash = hashes[idx]
                doc_id = batch_seen_hashes[content_hash]

                # Đưa vào bộ nhớ RAM
                self.vectors[doc_id] = {
                    "text": text,
                    "embedding": emb,
                    "metadata": metadatas[idx],
                }

                self.hash_index[content_hash] = doc_id
                ids[idx] = doc_id
            
            # CỰC KỲ QUAN TRỌNG: Có dữ liệu mới là đóng băng ghi ngay xuống ổ cứng
            self._save_to_disk()

        return ids

    def search(self, query: str, k: int = 5) -> List[Document]:
        """
        Thuật toán Tìm kiếm thực thể tương đồng (Cosine Similarity) bằng NumPy thuần.
        Giúp Chatbot lấy chính xác ngữ cảnh tài liệu học tập.
        """
        if not self.vectors:
            return []

        try:
            # 1. Chuyển đổi câu hỏi của người dùng thành Vector
            query_vector = self.embedder.embed_query(query)
            if not query_vector:
                return []
            
            q_vec = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)

            # Trường hợp vector câu hỏi bằng 0 tuyệt đối
            if q_norm == 0:
                return []

            results = []
            # 2. Quét tuyến tính qua toàn bộ kho tri thức đang có trên RAM
            for doc_id, doc_data in self.vectors.items():
                db_vec = np.array(doc_data["embedding"], dtype=np.float32)
                db_norm = np.linalg.norm(db_vec)
                
                if db_norm == 0:
                    continue
                
                # Tính toán tích vô hướng Cosine Score
                score = float(np.dot(q_vec, db_vec) / (q_norm * db_norm))
                results.append((score, doc_data))

            # 3. Sắp xếp điểm số từ cao xuống thấp và lấy K phần tử tốt nhất
            results.sort(key=lambda x: x[0], reverse=True)
            top_k = results[:k]

            # 4. Đóng gói ngược lại thành cấu hình Document chuẩn của LangChain để RAGChain xử lý mượt mà
            langchain_docs = []
            for score, data in top_k:
                langchain_docs.append(
                    Document(page_content=data["text"], metadata=data["metadata"])
                )
            return langchain_docs

        except Exception as e:
            print(f" [Lỗi truy vấn tìm kiếm Vector]: {e}")
            return []

    def count(self) -> int:
        return len(self.vectors)

    def clear(self):
        """Xóa sạch não bộ hệ thống khi chạy lệnh nạp dữ liệu đính kèm cờ --clear"""
        print("Đang tiến hành dọn dẹp sạch sẽ kho tri thức cũ...")
        self.vectors = {}
        self.hash_index = {}
        if DB_FILEPATH.exists():
            DB_FILEPATH.unlink()
        print("[OK] Toàn bộ cơ sở dữ liệu đã được đưa về trạng thái trắng tinh khôi!")

    def get_sources(self) -> List[str]:
        """Trả về danh sách tên các tệp tin tài liệu đã học."""
        sources = set()
        for doc_data in self.vectors.values():
            meta = doc_data.get("metadata", {})
            if meta and "source" in meta:
                # Trích xuất lấy tên file ngắn gọn từ đường dẫn dài
                clean_src = meta["source"].split("/")[-1].split("\\")[-1]
                sources.add(clean_src)
        return sorted(list(sources))

    def __len__(self):
        return len(self.vectors)