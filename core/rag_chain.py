# -*- coding: utf-8 -*-
# core/rag_chain.py

import os
import google.genai as genai
from google.genai import types
from config import (
    GEMINI_API_KEY, GEMINI_MODEL, TEMPERATURE,
    MAX_TOKENS, TOP_K_RESULTS
)

# Giới hạn lượt chat giữ lại trong history (1 turn = 1 cặp user/model)
MAX_HISTORY_TURNS = 6


class RAGChain:
    def __init__(self, vector_store):
        self.vector_store = vector_store

        # 1. Khởi tạo Client Gemini (Mô hình chính)
        if not GEMINI_API_KEY:
            raise ValueError("Thiếu GEMINI_API_KEY trong file .env!")
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        self.gemini_model  = GEMINI_MODEL

        # 2. Khởi tạo Client Groq (Mô hình dự phòng) — import lazy tránh crash
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.groq_client  = None

        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
                print(f"  [OK] Groq dự phòng sẵn sàng | Model: {self.groq_model}")
            except ImportError:
                print("  [!] Package 'groq' chưa được cài. Chạy: pip install groq")
            except Exception as e:
                print(f"  [!] Khởi tạo Groq thất bại: {e}")

        self.system_instruction = (
            "BẠN LÀ TRỢ LÝ GIẢNG DẠY DSA THÔNG MINH. QUY TẮC BẮT BUỘC:\n\n"
            "1. XỬ LÝ CHÀO HỎI: Nếu người dùng CHỈ chào hỏi, hãy đáp lại thân mật, ngắn gọn.\n"
            "2. XỬ LÝ CODE: Nếu học sinh gửi code: phân tích lỗi sai -> Sửa code trong ``` -> Giải thích lý thuyết.\n"
            "3. XỬ LÝ LÝ THUYẾT: Sử dụng ngữ cảnh giáo trình được cung cấp để trả lời.\n"
            "4. ĐỊNH DẠNG: Mỗi đoạn mã phải nằm trong khối ```. Trả lời hoàn toàn bằng Tiếng Việt."
        )

        # Lịch sử chung cho cả 2 mảng, định dạng: [{"role": "user"/"assistant", "content": ...}]
        self.history = []

    # ------------------------------------------------------------------
    def _trim_history(self):
        """Giữ lại tối đa MAX_HISTORY_TURNS lượt cuối, đảm bảo đầu luôn là user."""
        max_items = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_items:
            self.history = self.history[-max_items:]
            # Đảm bảo không bắt đầu bằng phản hồi của trợ lý
            if self.history and self.history[0]["role"] == "assistant":
                self.history.pop(0)

    # ------------------------------------------------------------------
    def _call_gemini(self, prompt_rag: str) -> str:
        """Xây dựng contents stateless và gọi Gemini API."""
        contents = []

        # Map history sang định dạng Gemini: "assistant" -> "model"
        for msg in self.history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        # Thêm prompt chứa context vào lượt cuối của người dùng
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_rag)]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
        )

        response = self.gemini_client.models.generate_content(
            model=self.gemini_model, contents=contents, config=config
        )

        if not response or not hasattr(response, "text") or not response.text:
            raise RuntimeError("Gemini trả về response trống hoặc không hợp lệ")

        return response.text

    # ------------------------------------------------------------------
    def _call_groq(self, prompt_rag: str) -> str:
        """Gọi Groq API với lịch sử sạch."""
        if not self.groq_client:
            raise RuntimeError("Groq chưa được cấu hình hoặc khởi tạo lỗi")

        messages = [{"role": "system", "content": self.system_instruction}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": prompt_rag})

        chat_completion = self.groq_client.chat.completions.create(
            messages=messages,
            model=self.groq_model,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        # Kiểm tra choices trước khi truy cập [0] để tránh IndexError
        if not chat_completion.choices:
            raise RuntimeError("Groq trả về response trống (choices = [])")

        return chat_completion.choices[0].message.content

    # ------------------------------------------------------------------
    def query(self, question: str) -> dict:
        """Truy vấn RAG và sinh câu trả lời bằng cơ chế Hybrid Fallback."""

        # BƯỚC 1: TRUY VẤN TÀI LIỆU (RAG)
        chunks       = self.vector_store.search(question, k=TOP_K_RESULTS)
        context_text = "\n\n".join([c.page_content for c in chunks]) if chunks else ""

        prompt_rag = f"""NGỮ CẢNH HỖ TRỢ TỪ GIÁO TRÌNH:
{context_text if context_text else "Không tìm thấy tài liệu phù hợp trong DB."}

CÂU HỎI CỦA SINH VIÊN:
{question}

HƯỚNG DẪN TRẢ LỜI:
- Trả lời thẳng vào vấn đề.
- TUYỆT ĐỐI KHÔNG dùng cụm từ 'Dựa trên giáo trình được cung cấp'.
- TRẢ LỜI HOÀN TOÀN BẰNG TIẾNG VIỆT."""

        answer     = ""
        model_used = ""

        # BƯỚC 2: SINH VĂN BẢN (HYBRID FALLBACK)
        try:
            # PHƯƠNG ÁN 1: GOOGLE GEMINI
            print("[Gemini] Đang xử lý câu hỏi...")
            answer     = self._call_gemini(prompt_rag)
            model_used = f"Gemini ({self.gemini_model})"

        except Exception as gemini_error:
            # PHƯƠNG ÁN 2: GROQ DỰ PHÒNG
            print(f"[!] Gemini lỗi ({gemini_error}). Kích hoạt Groq dự phòng...")
            try:
                answer     = self._call_groq(prompt_rag)
                model_used = f"Groq ({self.groq_model})"
            except Exception as groq_error:
                # SỬA LỖI: Tránh trả lỗi thô kỹ thuật làm bẩn giao diện hiển thị của người dùng
                print(f"[CRITICAL] Hệ thống sập hoàn toàn!\n- Gemini: {gemini_error}\n- Groq: {groq_error}")
                answer     = "Xin lỗi em, hệ thống máy chủ của trợ lý ảo đang quá tải hoặc gặp sự cố kỹ thuật ngắn hạn. Em vui lòng thử gửi lại câu hỏi sau vài giây nhé!"
                model_used = "Error/None"

        # BƯỚC 3: CẬP NHẬT LỊCH SỬ (Chỉ lưu câu hỏi gốc khi AI phản hồi thành công thực sự)
        # SỬA LỖI LOGIC: Không lưu các lượt hội thoại sinh lỗi hệ thống để tránh làm hỏng cấu trúc ngữ cảnh tiếp theo
        if model_used != "Error/None":
            self.history.append({"role": "user",      "content": question})
            self.history.append({"role": "assistant", "content": answer})

        # Cắt bớt lịch sử ngay sau khi append để kiểm soát chính xác kích thước mảng ngữ cảnh
        self._trim_history()

        # BƯỚC 4: TRÍCH XUẤT NGUỒN TÀI LIỆU
        sources = list({
            c.metadata.get("source", "").split("/")[-1].split("\\")[-1]
            for c in chunks
            if c.metadata.get("source")
        })

        return {
            "answer":      answer,
            "sources":     sources,
            "has_context": bool(chunks),
            "model_used":  model_used,
        }

    # ------------------------------------------------------------------
    def clear_history(self):
        self.history = []