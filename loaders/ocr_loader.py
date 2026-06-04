# -*- coding: utf-8 -*-
# loaders/ocr_loader.py
# Đọc file PDF scan (dùng OCR - Tesseract)
# Yêu cầu: cài Tesseract OCR + gói tiếng Việt

import os
import re
from langchain_core.documents import Document

# ============================================================
# CẤU HÌNH ĐƯỜNG DẪN WINDOWS (Hãy sửa lại cho đúng với máy của bạn)
# ============================================================
TESSERACT_PATH_WINDOWS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH_WINDOWS = r"C:\Program Files\poppler\Library\bin"  # Đường dẫn tới thư mục 'bin' của Poppler sau khi giải nén


def load_pdf_ocr(file_path: str, language: str = "vie+eng") -> list[Document]:
    """
    Đọc PDF scan bằng OCR (Optical Character Recognition).
    Hỗ trợ tiếng Việt và tiếng Anh.
    
    Cài đặt Tesseract:
        Windows: https://github.com/UB-Mannheim/tesseract/wiki
        Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-vie
        macOS:   brew install tesseract tesseract-lang
    
    Args:
        file_path: Đường dẫn PDF scan
        language: Ngôn ngữ OCR (mặc định: vie+eng)
        
    Returns:
        Danh sách Document
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
        from PIL import Image
        
        # Tự động gán đường dẫn Tesseract nếu chạy trên môi trường Windows
        if os.name == 'nt':
            if os.path.exists(TESSERACT_PATH_WINDOWS):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_WINDOWS
            else:
                print(f"⚠️ Cảnh báo: Không tìm thấy Tesseract tại: {TESSERACT_PATH_WINDOWS}")
                print("   Hãy kiểm tra lại đường dẫn cài đặt hoặc cập nhật biến TESSERACT_PATH_WINDOWS ở đầu file.")
                
    except ImportError as e:
        print(f"❌ Thiếu thư viện OCR: {e}")
        print("   Chạy: pip install pytesseract pdf2image Pillow")
        return []

    docs = []
    filename = os.path.basename(file_path)
    
    print(f"🔍 Đang OCR PDF scan: {filename}")
    print(f"   Ngôn ngữ: {language}")
    
    try:
        # Thiết lập tham số chuyển đổi PDF thành ảnh
        convert_kwargs = {
            "dpi": 300,
            "fmt": "PNG",
            "thread_count": 2
        }
        
        # Nếu là Windows và thư mục Poppler tồn tại, thêm cấu hình poppler_path để tránh crash lỗi
        if os.name == 'nt' and os.path.exists(POPPLER_PATH_WINDOWS):
            convert_kwargs["poppler_path"] = POPPLER_PATH_WINDOWS
        
        print("   Đang chuyển đổi PDF → ảnh...")
        images = convert_from_path(file_path, **convert_kwargs)
        
        total_pages = len(images)
        print(f"   Tổng số trang: {total_pages}")
        
        for page_num, image in enumerate(images, start=1):
            print(f"   OCR trang {page_num}/{total_pages}...", end="\r")
            
            # Tiền xử lý ảnh (Grayscale, Tăng tương phản, Làm sắc nét) để tăng độ chính xác OCR
            image = preprocess_image(image)
            
            # Chạy Tesseract OCR trích xuất văn bản
            text = pytesseract.image_to_string(
                image,
                lang=language,
                config="--oem 3 --psm 6"  # OEM=3: Tesseract+LSTM, PSM=6: Coi toàn bộ là khối văn bản thống nhất
            )
            
            if text and text.strip():
                # Làm sạch văn bản nhưng bảo vệ cấu trúc code và ký hiệu thuật toán toán học
                cleaned_text = clean_ocr_text(text)
                
                doc = Document(
                    page_content=cleaned_text,
                    metadata={
                        "source": filename,
                        "source_type": "pdf_ocr",
                        "page": page_num,
                        "total_pages": total_pages,
                        "file_path": file_path,
                        "ocr_language": language,
                    }
                )
                docs.append(doc)
        
        print(f"\n   ✅ OCR thành công {len(docs)}/{total_pages} trang")
        
    except Exception as e:
        print(f"\n   ❌ Lỗi hệ thống khi OCR: {e}")
        
        # Hướng dẫn gỡ lỗi thân thiện dựa trên log lỗi nhận diện được
        error_msg = str(e).lower()
        if "tesseract" in error_msg or "tesseract_cmd" in error_msg:
            print("   💡 Hướng dẫn sửa: Hệ thống chưa tìm thấy bộ cài Tesseract OCR thực thi.")
            print(f"   Vui lòng sửa biến 'TESSERACT_PATH_WINDOWS' ở đầu file này khớp với thư mục cài của bạn.")
        elif "poppler" in error_msg:
            print("   💡 Hướng dẫn sửa: Thiếu công cụ Poppler để xử lý phân trang PDF.")
            print("   Tải Poppler cho Windows, giải nén và trỏ biến 'POPPLER_PATH_WINDOWS' ở đầu file về thư mục 'bin'.")
            
    return docs


def preprocess_image(image):
    """Tiền xử lý hình ảnh giúp cải thiện đáng kể độ chính xác của bộ nhận diện OCR."""
    try:
        from PIL import ImageFilter, ImageEnhance
        
        # Bước 1: Chuyển ảnh màu sang ảnh xám (Grayscale)
        image = image.convert("L")
        
        # Bước 2: Tăng mạnh độ tương phản (Contrast) lên gấp 2 lần giúp chữ đen nổi bật trên nền giấy trắng
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Bước 3: Áp bộ lọc làm sắc nét viền chữ (Sharpen) chống nhòe
        image = image.filter(ImageFilter.SHARPEN)
        
        return image
    except Exception:
        return image


def clean_ocr_text(text: str) -> str:
    """
    Chuẩn hóa văn bản sau OCR.
    Giữ lại toàn bộ ký tự đặc biệt của code C/C++, Python, Java và ký hiệu thuật toán RAG.
    """
    # Xử lý các dòng trống thừa thãi sinh ra do lỗi xuống dòng ngẫu nhiên của OCR
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    text = '\n'.join(lines)
    
    # Gom cụm các khoảng trắng thừa liên tục trong cùng một dòng về duy nhất 1 khoảng trắng
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()