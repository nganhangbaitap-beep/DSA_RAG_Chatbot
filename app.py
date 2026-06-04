# -*- coding: utf-8 -*-
# app.py

import os
import sys
import streamlit as st
from datetime import datetime
from collections import Counter

import gspread
from google.oauth2.service_account import Credentials

# Nạp các cấu hình cũ của bạn
from config import GOOGLE_SHEET_NAME, TAB_DANH_SACH, TAB_LICH_SU
from core import VectorStore, GeminiEmbedder, RAGChain

# Cấu hình trang Streamlit
st.set_page_config(page_title="DSA Assistant", page_icon="🤖", layout="centered")

# ============================================================
# HÀM KẾT NỐI GOOGLE SHEETS BẢO MẬT (Tương thích Hugging Face)
# ============================================================
def get_google_sheet():
    """Kết nối tới Google Sheet bằng file JSON bảo mật."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Ở local: đọc từ file google_creds.json
    # Trên Hugging Face: Bạn copy nội dung file JSON dán vào Secret tên GOOGLE_CREDS_JSON
    if "GOOGLE_CREDS_JSON" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # Chạy local
        if not os.path.exists("google_creds.json"):
            st.error("❌ Thiếu file google_creds.json để kết nối Google Sheets!")
            st.stop()
        creds = Credentials.from_service_account_file("google_creds.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME)


# ============================================================
# HÀM XỬ LÝ ĐỒNG BỘ KHI ĐĂNG XUẤT (LƯU LỊCH SỬ)
# ============================================================
def xu_ly_dang_xuat_va_luu_sheets(mssv, list_questions):
    """Tính toán dữ liệu và đẩy lên Google Sheets khi học sinh đăng xuất."""
    if not list_questions:
        total_q = 0
        most_common_q = "Không đặt câu hỏi nào"
    else:
        total_q = len(list_questions)
        # Sử dụng Counter để tìm câu hỏi xuất hiện nhiều nhất (hoặc trùng lặp nhất)
        occurence_count = Counter(list_questions)
        most_common_q = occurence_count.most_common(1)[0][0]
        # Nếu câu hỏi quá dài, cắt bớt để hiển thị đẹp trên Sheet
        if len(most_common_q) > 150:
            most_common_q = most_common_q[:147] + "..."

    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        sh = get_google_sheet()
        wks = sh.worksheet(TAB_LICH_SU)
        
        # Thêm một dòng mới vào cuối bảng LichSuDangXuat
        # Cột: Mã SV | Thời Gian Đăng Xuất | Tổng Số Câu Hỏi | Câu Hỏi Được Hỏi Nhiều Nhất
        wks.append_row([mssv, thoi_gian, total_q, most_common_q])
        return True
    except Exception as e:
        print(f"Lỗi ghi dữ liệu đăng xuất lên Sheets: {e}")
        return False


# ============================================================
# KHỞI TẠO HỆ THỐNG RAG VÀ PHIÊN LÀM VIỆC (SESSION STATE)
# ============================================================
if "rag_chain" not in st.session_state:
    try:
        embedder = GeminiEmbedder()
        vs = VectorStore(embedder)
        st.session_state.rag_chain = RAGChain(vs)
    except Exception as e:
        st.error(f"Lỗi khởi tạo hệ thống AI: {e}")
        st.stop()

# Biến kiểm soát trạng thái đăng nhập
if "authenticated_mssv" not in st.session_state:
    st.session_state.authenticated_mssv = None

# Mảng lưu danh sách các câu hỏi dạng text thuần túy của học sinh trong phiên này
if "session_questions" not in st.session_state:
    st.session_state.session_questions = []

# Mảng hiển thị UI chat
if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# MÀN HÌNH 1: GIAO DIỆN ĐĂNG NHẬP (KIỂM TRA CHÍNH XÁC MASV)
# ============================================================
if not st.session_state.authenticated_mssv:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🤖 DSA Assistant - Xác Thực Sinh Viên</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        input_mssv = st.text_input("Nhập Mã Số Sinh Viên (MSSV):", placeholder="Ví dụ: B20DCCN123").strip().upper()
        submit_btn = st.form_submit_button("Đăng Nhập Vào Hệ Thống")
        
        if submit_btn:
            if not input_mssv:
                st.warning("⚠️ Vui lòng không để trống Mã số sinh viên!")
            else:
                with st.spinner("🔄 Đang kiểm tra danh sách tài khoản từ Google Sheets..."):
                    try:
                        sh = get_google_sheet()
                        wks = sh.worksheet(TAB_DANH_SACH)
                        
                        # Lấy toàn bộ giá trị của cột số 1 (Cột MSSV)
                        danh_sach_mssv_hop_le = [str(x).strip().upper() for x in wks.col_values(1)]
                        
                        # Kiểm tra xem MASV học sinh nhập có trong danh sách không
                        if input_mssv in danh_sach_mssv_hop_le:
                            st.session_state.authenticated_mssv = input_mssv
                            st.session_state.session_questions = []
                            st.session_state.messages = [{"role": "assistant", "content": f"Chào em **{input_mssv}**! Anh là trợ lý học tập môn DSA. Hôm nay em cần hỗ trợ gì về cấu trúc dữ liệu, giải thuật hoặc sửa code?"}]
                            st.success("✅ Xác thực thành công!")
                            st.rerun()
                        else:
                            # BÁO LỖI NẾU ĐĂNG NHẬP KHÔNG ĐÚNG
                            st.error("❌ Mã số sinh viên không chính xác hoặc không nằm trong danh sách được cấp phép của Giáo viên!")
                    except Exception as e:
                        st.error(f"⚠️ Không thể kết nối tới Google Sheets dữ liệu. Lỗi: {e}")
    st.stop()


# ============================================================
# MÀN HÌNH 2: GIAO DIỆN CHAT CHÍNH (KHI ĐÃ ĐĂNG NHẬP)
# ============================================================
current_user = st.session_state.authenticated_mssv

# Thanh Sidebar hiển thị thông tin và nút Đăng xuất
st.sidebar.markdown(f"👤 **Sinh viên:** `{current_user}`")

if st.sidebar.button("🚪 Đăng xuất & Nộp báo cáo"):
    with st.spinner("🔄 Đang đồng bộ lịch sử buổi học lên Google Sheets của Giáo viên..."):
        # Gọi hàm đồng bộ dữ liệu
        thanh_cong = xu_ly_dang_xuat_va_luu_sheets(current_user, st.session_state.session_questions)
        if thanh_cong:
            st.sidebar.success("Đã lưu báo cáo!")
        
        # Reset toàn bộ trạng thái phiên làm việc để quay về màn hình đăng nhập
        st.session_state.authenticated_mssv = None
        st.session_state.session_questions = []
        st.session_state.messages = []
        st.rerun()

st.title(f"🤖 DSA Assistant (Phòng học của {current_user})")

# Hiển thị lại các tin nhắn cũ trong phiên chat hiện tại
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ô nhập câu hỏi của Học sinh
if prompt := st.chat_input("Nhập câu hỏi lý thuyết hoặc dán code cần debug vào đây..."):
    
    # 1. Hiển thị tin nhắn của học sinh lên UI
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Lưu câu hỏi vào danh sách thống kê câu hỏi của phiên này
    st.session_state.session_questions.append(prompt)
    
    # 3. Gọi RAGChain xử lý câu trả lời
    with st.chat_message("assistant"):
        with st.spinner("🤖 Đang suy nghĩ..."):
            try:
                res = st.session_state.rag_chain.query(prompt)
                ans = res.get("answer", "Hệ thống không trả về câu trả lời.")
                sources = res.get("sources", [])
                
                # Hiển thị câu trả lời
                st.markdown(ans)
                if sources:
                    st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
                
                # Lưu vào lịch sử hiển thị UI
                st.session_state.messages.append({"role": "assistant", "content": ans})
                
            except Exception as e:
                err = f"❌ Đã xảy ra lỗi hệ thống: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})