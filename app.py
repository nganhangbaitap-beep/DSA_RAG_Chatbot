# -*- coding: utf-8 -*-
# app.py

import os
import time
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

# Nạp các cấu hình hằng số từ file config
from config import GOOGLE_SHEET_NAME, TAB_DANH_SACH, TAB_LICH_SU
# Nạp các module xử lý AI từ thư mục core
from core import VectorStore, GeminiEmbedder, RAGChain 

# Cấu hình giao diện trang Streamlit
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
    
    # Ưu tiên lấy từ biến môi trường (Hugging Face / Server)
    if "GOOGLE_CREDS_JSON" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # Lấy từ file cục bộ (Chạy Local trên máy tính)
        if not os.path.exists("google_creds.json"):
            st.error("❌ Thiếu file google_creds.json để kết nối Google Sheets!")
            st.stop()
        creds = Credentials.from_service_account_file("google_creds.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME)


# ============================================================
# HÀM XỬ LÝ ĐỒNG BỘ CHẠY NGẦM KHI ĐĂNG XUẤT (ẨN THÔNG BÁO)
# ============================================================
def xu_ly_dang_xuat_va_luu_sheets(mssv, chat_history):
    """Ghi dữ liệu âm thầm, trả về True nếu thành công, False nếu thất bại."""

    # Chuỗi từ chối nhận diện câu lạc đề
    CAU_TU_CHOI_MAC_DINH = "Không trả lời về thời tiết, đời tư, chính trị, hoặc chủ đề hoàn toàn không liên quan đến học tập lập trình" 
    
    rows_to_append = []
    
    # Khởi tạo múi giờ Việt Nam (UTC+7)
    tz_vietnam = timezone(timedelta(hours=7))
    thoi_gian_vn = datetime.now(tz_vietnam).strftime("%Y-%m-%d %H:%M:%S")

    current_question = ""
    for msg in chat_history:
        if msg["role"] == "user":
            current_question = msg["content"].strip()
        elif msg["role"] == "assistant" and current_question:
            ai_response = msg["content"]
            
            # Bộ lọc kép bảo vệ dữ liệu sạch
            if len(current_question) > 5 and CAU_TU_CHOI_MAC_DINH not in ai_response:
                rows_to_append.append([mssv, thoi_gian_vn, current_question])
            
            current_question = ""

    # Nếu không có dữ liệu để ghi, coi như hoàn thành âm thầm
    if not rows_to_append:
        return True  

    # Tiến hành ghi dữ liệu ngầm lên Google Sheets
    try:
        sh  = get_google_sheet()
        wks = sh.worksheet(TAB_LICH_SU)
        wks.append_rows(rows_to_append) 
        return True
    except Exception as e:
        # Lỗi in ra màn hình Terminal/Log hệ thống của Giáo viên để kiểm tra lại khi cần
        print(f"--- [LOG HỆ THỐNG LỖI] {e} ---")
        return f"Lỗi API: {e}" # Trả về chuỗi lỗi chi tiết phục vụ Dev Mode


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

if "authenticated_mssv" not in st.session_state:
    st.session_state.authenticated_mssv = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# MÀN HÌNH 1: GIAO DIỆN ĐĂNG NHẬP
# ============================================================
if not st.session_state.authenticated_mssv:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🤖 DSA Assistant - Xác Thực Sinh Viên</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        input_mssv = st.text_input("Nhập Mã Số Sinh Viên (MSSV):", placeholder="Ví dụ: SV123").strip().upper()
        submit_btn = st.form_submit_button("Đăng Nhập Vào Hệ Thống")
        
        if submit_btn:
            if not input_mssv:
                st.warning("⚠️ Vui lòng không để trống Mã số sinh viên!")
            else:
                with st.spinner("🔄 Đang kiểm tra danh sách tài khoản..."):
                    try:
                        sh = get_google_sheet()
                        wks = sh.worksheet(TAB_DANH_SACH)
                        
                        danh_sach_mssv_hop_le = [str(x).strip().upper() for x in wks.col_values(1)]
                        
                        if input_mssv in danh_sach_mssv_hop_le:
                            st.session_state.authenticated_mssv = input_mssv
                            st.session_state.messages = [{"role": "assistant", "content": f"Chào bạn **{input_mssv}**! Tôi là trợ lý học tập môn DSA. Hôm nay bạn cần hỗ trợ gì về cấu trúc dữ liệu, giải thuật hoặc sửa code?"}]
                            st.success("✅ Xác thực thành công!")
                            st.rerun()
                        else:
                            st.error("❌ Mã số sinh viên không chính xác hoặc không nằm trong danh sách lớp!")
                    except Exception as e:
                        st.error(f"⚠️ Không thể kết nối tới Google Sheets dữ liệu. Lỗi: {e}")
    st.stop()


# ============================================================
# MÀN HÌNH 2: GIAO DIỆN CHAT CHÍNH
# ============================================================
current_user = st.session_state.authenticated_mssv

st.sidebar.markdown(f"👤 **Sinh viên:** `{current_user}`")

# Khi người dùng nhấn nút Đăng xuất
if st.sidebar.button("🚪 Đăng xuất"):
    # 1. Gọi hàm xử lý lưu dữ liệu lên Excel
    ket_qua = xu_ly_dang_xuat_va_luu_sheets(current_user, st.session_state.messages)
    
    # 2. CHẾ ĐỘ KIỂM TRA RIÊNG (DEV MODE): Chỉ kích hoạt nếu user là ADMIN hoặc GV_TEST
    if current_user in ["ADMIN", "GV_TEST"]:
        if ket_qua is True:
            st.sidebar.success("🔑 [Dev Mode] Đã lưu ngầm vào Sheets thành công!")
        else:
            st.sidebar.error(f"❌ [Dev Mode] Thất bại! {ket_qua}")
        # Giữ lại giao diện 2.5 giây để Giáo viên kịp đọc kết quả kiểm tra
        time.sleep(2.5)
    
    # 3. Reset phiên làm việc để đẩy người dùng ra màn hình đăng nhập ban đầu
    st.session_state.authenticated_mssv = None
    st.session_state.messages = []
    st.rerun()

st.title(f"🤖 DSA Assistant (Phòng học của {current_user})")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi lý thuyết hoặc dán code cần debug vào đây..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🤖 Đang suy nghĩ..."):
            try:
                res = st.session_state.rag_chain.query(prompt)
                ans = res.get("answer", "Hệ thống không trả về câu trả lời.")
                sources = res.get("sources", [])
                
                st.markdown(ans)
                if sources:
                    st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
                
                st.session_state.messages.append({"role": "assistant", "content": ans})
                
            except Exception as e:
                err = f"❌ Đã xảy ra lỗi hệ thống. Có thể do quá tải, thử lại sau. (Lỗi: {e})"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})