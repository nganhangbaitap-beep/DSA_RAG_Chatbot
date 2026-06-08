# -*- coding: utf-8 -*-
# app.py

import os
import time
import threading
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

# Nạp các cấu hình hằng số từ file config
from config import GOOGLE_SHEET_NAME, TAB_DANH_SACH, TAB_LICH_SU
# Nạp các module xử lý AI từ thư mục core
from core import VectorStore, GeminiEmbedder, RAGChain 

# Cấu hình giao diện trang Streamlit (Xóa bỏ toàn bộ phần CSS Hack cũ để giao diện tự động co giãn chuẩn)
st.set_page_config(page_title="DSA Assistant", page_icon="🤖", layout="centered")


# ============================================================
# HÀM KẾT NỐI GOOGLE SHEETS BẢO MẬT
# ============================================================
def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "GOOGLE_CREDS_JSON" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        if not os.path.exists("google_creds.json"):
            st.error("❌ Thiếu file google_creds.json để kết nối Google Sheets!")
            st.stop()
        creds = Credentials.from_service_account_file("google_creds.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME)


# ============================================================
# HÀM GHI LOG REAL-TIME (CHẠY NGẦM BẰNG THREADING)
# ============================================================
def ghi_log_realtime(mssv, cau_hoi, cau_tra_loi):
    if "Xin lỗi, tôi là trợ lý ảo chuyên trách" in cau_tra_loi:
        return 
        
    if len(cau_hoi.strip()) <= 5:
        return

    clean_question = cau_hoi.strip()
    clean_question = clean_question.replace("\r\n", " ➔ ").replace("\n", " ➔ ").replace("\r", " ➔ ")

    tz_vietnam = timezone(timedelta(hours=7))
    thoi_gian_vn = datetime.now(tz_vietnam).strftime("%Y-%m-%d %H:%M:%S")

    try:
        sh  = get_google_sheet()
        wks = sh.worksheet(TAB_LICH_SU)
        values_in_col_a = wks.col_values(1)
        next_row = len(values_in_col_a) + 1
        wks.insert_rows([[mssv, thoi_gian_vn, clean_question]], row=next_row) 
    except Exception as e:
        print(f"--- [LOG LỖI GHI SHEETS] {e} ---")


# ============================================================
# KHỞI TẠO HỆ THỐNG RAG VÀ PHIÊN LÀM VIỆC
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

# --- 🛠️ ĐƯA THÔNG TIN & NÚT ĐĂNG XUẤT VÀO THANH BÊN (SIDEBAR) 🛠️ ---
with st.sidebar:
    st.markdown(f"### 👤 Tài khoản: **{current_user}**")
    st.caption("Trợ lý học tập chuyên trách môn DSA")
    st.markdown("---")
    
    # Nút Đăng xuất dạng Primary (Màu đỏ sẫm mặc định của Streamlit) chiếm trọn chiều rộng thanh bên
    if st.button("🚪 Đăng xuất khỏi phòng học", use_container_width=True, type="primary"):
        st.session_state.authenticated_mssv = None
        st.session_state.messages = []
        st.rerun()

# --- KHÔNG GIAN CHAT CHÍNH ---
st.title("🤖 DSA Assistant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Khung nhập liệu câu hỏi chat - BÂY GIỜ HOÀN TOÀN KHÔNG BỊ LỖI HIỂN THỊ
if prompt := st.chat_input("Nhập câu hỏi lý thuyết hoặc dán code cần debug vào đây..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        try:
            res = st.session_state.rag_chain.query(prompt)
            ans = res.get("answer", "Hệ thống không trả về câu trả lời.")
            sources = res.get("sources", [])
            
            def stream_generator():
                for word in ans.split(" "):
                    yield word + " "
                    time.sleep(0.03)
                    
            st.write_stream(stream_generator)
            
            if sources:
                st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
            
            st.session_state.messages.append({"role": "assistant", "content": ans})
            
            threading.Thread(
                target=ghi_log_realtime, 
                args=(current_user, prompt, ans)
            ).start()
            
            st.rerun()
            
        except Exception as e:
            err = f"❌ Đã xảy ra lỗi hệ thống. Có thể do quá tải, thử lại sau. (Lỗi: {e})"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})