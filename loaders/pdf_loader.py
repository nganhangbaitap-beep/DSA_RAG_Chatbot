# loaders/pdf_loader.py
# Đọc file PDF thông thường (có text layer)

import os
import pdfplumber
from pypdf import PdfReader
from langchain_core.documents import Document


def load_pdf(file_path: str) -> list[Document]:
    """
    Đọc file PDF có text layer (không cần OCR).
    Thử pdfplumber trước, fallback sang pypdf nếu lỗi.
    
    Args:
        file_path: Đường dẫn đến file PDF
        
    Returns:
        Danh sách Document (mỗi trang = 1 document)
    """
    docs = []
    filename = os.path.basename(file_path)
    
    print(f"📄 Đang đọc PDF: {filename}")
    
    # Thử đọc bằng pdfplumber (chất lượng cao hơn)
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                
                # Trích xuất bảng nếu có
                tables = page.extract_tables()
                table_text = ""
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                table_text += " | ".join(
                                    str(cell) if cell else "" for cell in row
                                ) + "\n"
                
                full_text = ""
                if text:
                    full_text += text.strip()
                if table_text:
                    full_text += "\n[BẢNG]\n" + table_text
                
                if full_text.strip():
                    doc = Document(
                        page_content=full_text,
                        metadata={
                            "source": filename,
                            "source_type": "pdf",
                            "page": page_num,
                            "total_pages": total_pages,
                            "file_path": file_path,
                        }
                    )
                    docs.append(doc)
                    
        print(f"   ✅ Đọc thành công {len(docs)}/{total_pages} trang")
        
    except Exception as e:
        print(f"   ⚠️ pdfplumber thất bại ({e}), thử pypdf...")
        
        # Fallback: pypdf
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    doc = Document(
                        page_content=text.strip(),
                        metadata={
                            "source": filename,
                            "source_type": "pdf",
                            "page": page_num,
                            "total_pages": total_pages,
                            "file_path": file_path,
                        }
                    )
                    docs.append(doc)
                    
            print(f"   ✅ pypdf đọc thành công {len(docs)}/{total_pages} trang")
            
        except Exception as e2:
            print(f"   ❌ Lỗi đọc PDF: {e2}")
            
    return docs
