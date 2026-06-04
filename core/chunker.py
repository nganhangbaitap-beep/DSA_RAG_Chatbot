# core/chunker.py
# Chia nhỏ văn bản thành các chunk

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import CHUNK_SIZE, CHUNK_OVERLAP


def split_documents(documents: list[Document]) -> list[Document]:
    """
    Chia tài liệu thành các chunk nhỏ hơn.
    
    Chiến lược: RecursiveCharacterTextSplitter
    - Ưu tiên tách tại: paragraph -> sentence -> word -> character
    - Giữ lại metadata từ document gốc
    
    Args:
        documents: Danh sách Document cần chia
        
    Returns:
        Danh sách Document đã chia nhỏ
    """
    if not documents:
        return []
    
    # Splitter tối ưu cho văn bản học thuật Việt-Anh
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=[
            "\n\n",   # Paragraph break
            "\n",     # Line break
            "。",     # Câu tiếng Nhật (nếu có)
            ".",      # Dấu chấm câu
            "!",
            "?",
            ";",
            ",",
            " ",
            "",
        ]
    )
    
    chunks = splitter.split_documents(documents)
    
    # Thêm chunk index vào metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["chunk_size"] = len(chunk.page_content)
    
    # Thống kê
    total_chars = sum(len(doc.page_content) for doc in documents)
    avg_chunk = sum(len(c.page_content) for c in chunks) / len(chunks) if chunks else 0
    
    print(f"\n📦 Chunking hoàn tất:")
    print(f"   Documents gốc: {len(documents)}")
    print(f"   Tổng ký tự: {total_chars:,}")
    print(f"   Số chunks: {len(chunks)}")
    print(f"   Chunk size trung bình: {avg_chunk:.0f} ký tự")
    print(f"   Cấu hình: size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    
    return chunks
