import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("--- DANH SÁCH MODEL KHẢ DỤNG ---")
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            # In ra tên để bạn copy trực tiếp vào file .env
            print(f"Model Name: {m.name}") 
except Exception as e:
    print(f"Lỗi: {e}")