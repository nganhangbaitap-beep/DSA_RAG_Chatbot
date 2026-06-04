# test_ai.py
import os
from dotenv import load_dotenv
from google import genai

# Tải các biến môi trường từ file .env
load_dotenv()

# Lấy thông tin cấu hình
API_KEY = os.getenv("GEMINI_API_KEY")
# Nếu trong .env không khai báo, mặc định sẽ dùng gemini-1.5-flash
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

print("API KEY:", "OK" if API_KEY else "MISSING")
print("MODEL:", MODEL)

def test_gemini_connection():
    """Hàm kiểm tra kết nối tới API Google Gemini SDK mới."""
    if not API_KEY:
        print("\n❌ Lỗi: Chưa tìm thấy GEMINI_API_KEY. Vui lòng kiểm tra lại file .env")
        return

    # Khởi tạo Client theo chuẩn google-genai mới
    client = genai.Client(api_key=API_KEY)

    try:
        # Gọi API sinh văn bản
        print("🌐 Đang kiểm tra kết nối Gemini...")
        response = client.models.generate_content(
            model=MODEL,
            contents="Hãy nói 1 câu chào thật ngắn gọn."
        )

        print("\n✅ Gemini hoạt động tuyệt vời!")
        print("Phản hồi từ AI:", response.text)

    except Exception as e:
        print("\n❌ Lỗi cấu hình hoặc kết nối Gemini API:")
        print(str(e))

if __name__ == "__main__":
    test_gemini_connection()