# -*- coding: utf-8 -*-
# app.py

import os
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
# HÀM XỬ LÝ ĐỒNG BỘ KHI ĐĂNG XUẤT (LƯU LỊCH SỬ TINH GỌN)
# ============================================================
def xu_ly_dang_xuat_va_luu_sheets(mssv, chat_history):
    """Ghi từng câu hỏi DSA thành 1 dòng riêng, lọc bỏ câu ngắn và câu lạc đề, chuẩn hóa giờ VN."""

    # Chuỗi từ chối nhận diện câu lạc đề (khớp với SYSTEM_PROMPT trong config.py)
    CAU_TU_CHOI_MAC_DINH = "Không trả lời về thời tiết, đời tư, chính trị, hoặc chủ đề hoàn toàn không liên quan đến học tập lập trình" 
    
    rows_to_append = []
    
    # Khởi tạo múi giờ Việt Nam (UTC+7) để chạy chuẩn trên server quốc tế
    tz_vietnam = timezone(timedelta(hours=7))
    thoi_gian_vn = datetime.now(tz_vietnam).strftime("%Y-%m-%d %H:%M:%S")

    current_question = ""
    # Duyệt qua toàn bộ lịch sử hội thoại của sinh viên
    for msg in chat_history:
        if msg["role"] == "user":
            current_question = msg["content"].strip()
        elif msg["role"] == "assistant" and current_question:
            ai_response = msg["content"]
            
            # LỌC KÉP: Chỉ lấy câu hỏi dài hơn 5 ký tự và AI KHÔNG từ chối trả lời
            if len(current_question) > 5 and CAU_TU_CHOI_MAC_DINH not in ai_response:
                # Đóng gói dữ liệu thành mảng chuẩn: [Cột A, Cột B, Cột C]
                rows_to_append.append([mssv, thoi_gian_vn, current_question])
            
            # Reset biến để duyệt vòng lặp bắt cặp tiếp theo
            current_question = ""

    # Nếu sinh viên chỉ nhắn câu rác hoặc không hỏi gì hợp lệ thì bỏ qua không gọi Sheets API
    if not rows_to_append:
        return True  

    # Ghi dữ liệu hàng loạt (Batch Insert) siêu tốc lên Google Sheets
    try:
        sh  = get_google_sheet()
        wks = sh.worksheet(TAB_LICH_SU)
        wks.append_rows(rows_to_append) 
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

# Biến kiểm soát trạng thái đăng nhập MSSV
if "authenticated_mssv" not in st.session_state:
    st.session_state.authenticated_mssv = None

# Mảng lưu trữ toàn bộ hội thoại UI chat trong một phiên
if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# MÀN HÌNH 1: GIAO DIỆN ĐĂNG NHẬP (KIỂM TRA CHÍNH XÁC MSSV)
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
                        
                        # Lấy toàn bộ giá trị của cột số 1 (Cột MSSV)
                        danh_sach_mssv_hop_le = [str(x).strip().upper() for x in wks.col_values(1)]
                        
                        # Kiểm tra xem MSSV sinh viên nhập có khớp không
                        if input_mssv in danh_sach_mssv_hop_le:
                            st.session_state.authenticated_mssv = input_mssv
                            # Gửi tin nhắn chào mừng mặc định
                            st.session_state.messages = [{"role": "assistant", "content": f"Chào em **{input_mssv}**! Tôi là trợ lý học tập môn DSA. Hôm nay bạn cần hỗ trợ gì về cấu trúc dữ liệu, giải thuật hoặc sửa code?"}]
                            st.success("✅ Xác thực thành công!")
                            st.rerun()
                        else:
                            st.error("❌ Mã số sinh viên không chính xác hoặc không nằm trong danh sách lớp!")
                    except Exception as e:
                        st.error(f"⚠️ Không thể kết nối tới Google Sheets dữ liệu. Lỗi: {e}")
    st.stop()


# ============================================================
# MÀN HÌNH 2: GIAO DIỆN CHAT CHÍNH (KHI ĐÃ ĐĂNG NHẬP)
# ============================================================
current_user = st.session_state.authenticated_mssv

# Thanh Sidebar chứa nút Đăng xuất
st.sidebar.markdown(f"👤 **Sinh viên:** `{current_user}`")

if st.sidebar.button("🚪 Đăng xuất & Nộp báo cáo"):
    with st.spinner("🔄 Đang lọc dữ liệu và đồng bộ báo cáo lên Google Sheets..."):
        # Gọi hàm xử lý truyền vào toàn bộ lịch sử messages
        thanh_cong = xu_ly_dang_xuat_va_luu_sheets(current_user, st.session_state.messages)
        
        if thanh_cong:
            st.sidebar.success("Đã lưu báo cáo thành công!")
        else:
            st.sidebar.error("Lỗi đồng bộ dữ liệu!")
        
        # Reset toàn bộ trạng thái phiên làm việc để quay về màn hình đăng nhập
        st.session_state.authenticated_mssv = None
        st.session_state.messages = []
        st.rerun()

st.title(f"🤖 DSA Assistant (Phòng học của {current_user})")

# Render hiển thị lại các tin nhắn cũ trong phiên chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ô nhập dữ liệu Chat của Sinh viên
if prompt := st.chat_input("Nhập câu hỏi lý thuyết hoặc dán code cần debug vào đây..."):
    
    # 1. Hiển thị tin nhắn của sinh viên lên UI và lưu vào messages
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Gọi Hệ thống RAG xử lý câu trả lời
    with st.chat_message("assistant"):
        with st.spinner("🤖 Đang suy nghĩ..."):
            try:
                res = st.session_state.rag_chain.query(prompt)
                ans = res.get("answer", "Hệ thống không trả về câu trả lời.")
                sources = res.get("sources", [])
                
                # Hiển thị câu trả lời và Nguồn tài liệu tham khảo
                st.markdown(ans)
                if sources:
                    st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
                
                # Lưu câu trả lời của AI vào mảng UI
                st.session_state.messages.append({"role": "assistant", "content": ans})
                
            except Exception as e:
                err = f"❌ Đã xảy ra lỗi hệ thống. Có thể do quá tải, thử lại sau. (Lỗi: {e})"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})