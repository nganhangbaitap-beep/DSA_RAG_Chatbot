# -*- coding: utf-8 -*-
# app.py

import os
import time
import threading
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

from config import GOOGLE_SHEET_NAME, TAB_DANH_SACH, TAB_LICH_SU
from core import VectorStore, GeminiEmbedder, RAGChain 

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="DSA Learning System", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .topic-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #10a37f;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .topic-title {
        color: #10a37f !important;
        font-weight: bold !important;
        margin-bottom: 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CƠ SỞ DỮ LIỆU ĐỒNG BỘ NỘI DUNG 6 CHƯƠNG GIÁO TRÌNH
# ============================================================
CHAPTER_DATA = {
    1: {
        "title": "Chương 1: Thiết kế và phân tích giải thuật",
        "desc": "Nắm vững phương pháp đánh giá hiệu suất, thời gian chạy và tối ưu thuật toán.",
        "pdf": "https://docs.google.com/document/d/1WC2VmOU_jhVfGzH_mPsQhozCDDXSFCbfpHYIBfULr2o/edit",
        "topics": [
            {"name": "Độ phức tạp thuật toán", "detail": "Phân tích cú pháp tính toán thời gian, không gian và ký pháp Big O."},
            {"name": "Chiến lược thiết kế giải thuật", "detail": "Tìm hiểu các mô hình kinh điển: Chia để trị, Tham lam, Quy hoạch động."}
        ]
    },
    2: {
        "title": "Chương 2: Các kiểu dữ liệu cơ sở",
        "desc": "Hệ thống hóa các kiểu dữ liệu nền tảng cấu thành cấu trúc lớn.",
        "pdf": "https://docs.google.com/document/d/1eky8_mvFQfTl8kvt3pg9fDeR5Hhq1jsEz5RQrWVt7-M/edit",
        "topics": [
            {"name": "Kiểu dữ liệu trừu tượng", "detail": "Định nghĩa tổng quan và tầm quan trọng của mô hình ADT trong lập trình."},
            {"name": "Con trỏ & Quản lý bộ nhớ", "detail": "Cơ chế hoạt động của biến con trỏ, tham chiếu và cấp phát động vùng nhớ."}
        ]
    },
    3: {
        "title": "Chương 3: Mảng, danh sách",
        "desc": "Tổ chức và quản lý các kiến trúc dữ liệu tuyến tính.",
        "pdf": "https://docs.google.com/document/d/1W845YWZlPpKLogb_ECmsXSQoMqcrpfh4IhuZ-Xv7tZA/edit",
        "topics": [
            {"name": "Cấu trúc Danh sách liên kết", "detail": "So sánh Mảng tĩnh (Array) với Danh sách liên kết đơn, đôi (Linked List)."},
            {"name": "Ngăn xếp & Hàng đợi", "detail": "Nguyên lý hoạt động và ứng dụng thực tế của cấu trúc LIFO (Stack) và FIFO (Queue)."}
        ]
    },
    4: {
        "title": "Chương 4: Cây (Tree)",
        "desc": "Cấu trúc dữ liệu phi tuyến tính phân cấp.",
        "pdf": "https://docs.google.com/document/d/1j39PD2vDIkuzNDe6FK_AntIUSlUjttELZmeWXANeO1k/edit",
        "topics": [
            {"name": "Cây nhị phân và các phép duyệt", "detail": "Các thuật toán duyệt cây phổ biến: Tiền tự, Trung tự, Hậu tự."},
            {"name": "Cây tìm kiếm nhị phân (BST)", "detail": "Ứng dụng cấu trúc cây nhị phân để tối ưu hóa tốc độ tìm kiếm và chèn dữ liệu."}
        ]
    },
    5: {
        "title": "Chương 5: Sắp xếp (Sorting)",
        "desc": "Các kỹ thuật hoán đổi và sắp xếp dãy dữ liệu.",
        "pdf": "https://docs.google.com/document/d/1jDSv-XYq1l0iwsA-T-P9aFZy6nSn9zbMwjplUAewsoo/edit",
        "topics": [
            {"name": "Các thuật toán sắp xếp đơn giản", "detail": "Phân tích mã nguồn của: Sắp xếp đổi chỗ, Chèn, Lựa chọn."},
            {"name": "Các giải thuật nâng cao", "detail": "Cách thức vận hành chiến lược chia để trị qua Quick Sort và Merge Sort."}
        ]
    },
    6: {
        "title": "Chương 6: Tìm kiếm (Searching)",
        "desc": "Truy xuất dữ liệu hiệu quả trên các cấu trúc mảng.",
        "pdf": "https://docs.google.com/document/d/1txFeyednVsiMHqkbvG3WuHn4GejBETI_QaD24w1rxYY/edit",
        "topics": [
            {"name": "Tìm kiếm tuyến tính", "detail": "Áp dụng cho tập danh sách thô, chưa có thứ tự."},
            {"name": "Tìm kiếm nhị phân", "detail": "Giải thuật tối ưu cực nhanh áp dụng trên danh sách mảng đã được sắp xếp."}
        ]
    }
}

# ============================================================
# HÀM KẾT NỐI SHEETS VÀ LƯU LOG 
# ============================================================
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "GOOGLE_CREDS_JSON" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        if not os.path.exists("google_creds.json"):
            st.error("❌ Thiếu file google_creds.json để kết nối Google Sheets!")
            st.stop()
        creds = Credentials.from_service_account_file("google_creds.json", scopes=scopes)
    return gspread.authorize(creds).open(GOOGLE_SHEET_NAME)

def ghi_log_realtime(mssv, cau_hoi, cau_tra_loi):
    text_lower = cau_hoi.strip().lower()
    
    # 1. BỘ LỌC TỪ KHÓA RÁC: Chặn vĩnh viễn các câu chào hỏi từ phía sinh viên
    black_list = ["xin chào", "chào", "chào bạn", "hello", "hi", "alo", "test", "bot"]
    if text_lower in black_list: 
        return
        
    # 2. CHẶN LỜI CHÀO TỪ AI: Nếu AI trả lời câu chào mặc định, không lưu vào log
    if "Tôi là trợ lý học tập" in cau_tra_loi or "Tôi là trợ lý ảo chuyên trách" in cau_tra_loi:
        return
        
    # 3. Chặn các câu quá ngắn (< 5 ký tự)
    if len(text_lower) <= 5: 
        return
        
    # Xử lý ghi log nếu qua được màng lọc
    clean_question = cau_hoi.strip().replace("\n", " ➔ ")
    thoi_gian_vn = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")
    try:
        wks = get_google_sheet().worksheet(TAB_LICH_SU)
        wks.insert_rows([[mssv, thoi_gian_vn, clean_question]], row=len(wks.col_values(1)) + 1) 
    except Exception as e: 
        print(f"Log lỗi Sheets: {e}")

# ============================================================
# KHỞI TẠO BIẾN SESSION STATE VÀ KHUNG AI RAG CHATBOT
# ============================================================
if "rag_chain" not in st.session_state:
    try:
        st.session_state.rag_chain = RAGChain(VectorStore(GeminiEmbedder()))
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}"); st.stop()

if "authenticated_mssv" not in st.session_state: st.session_state.authenticated_mssv = None
if "messages" not in st.session_state: st.session_state.messages = []
if "current_page" not in st.session_state: st.session_state.current_page = "home"

# ============================================================
# MÀN HÌNH XÁC THỰC (LOGIN)
# ============================================================
if not st.session_state.authenticated_mssv:
    _, login_col, _ = st.columns([1, 2, 1])
    with login_col:
        st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom:0;'>📚</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #1e293b; margin-top:0;'>DSA Learning System</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom:25px;'>Cấu trúc Dữ liệu & Giải thuật — Khoa CNTT</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            input_mssv = st.text_input("MÃ SINH VIÊN:", placeholder="Nhập Mã SV (VD: SV01)").strip().upper()
            submit_btn = st.form_submit_button("VÀO LỚP HỌC", use_container_width=True)
            
            if submit_btn:
                if not input_mssv:
                    st.error("⚠ Vui lòng nhập Mã Sinh Viên!")
                elif input_mssv == "ADMIN":
                    st.session_state.authenticated_mssv = "ADMIN"
                    st.session_state.messages = [{"role": "assistant", "content": "Xin chào Quản trị viên! Bạn vừa truy cập vào phòng điều khiển hệ thống."}]
                    st.rerun()
                else:
                    with st.spinner("Đang tra cứu dữ liệu..."):
                        try:
                            wks = get_google_sheet().worksheet(TAB_DANH_SACH)
                            valid_students = [str(x).strip().upper() for x in wks.col_values(1)]
                            
                            if input_mssv in valid_students:
                                st.session_state.authenticated_mssv = input_mssv
                                st.session_state.messages = [{"role": "assistant", "content": f"Chào bạn **{input_mssv}**! Tôi là trợ lý học tập môn CTDL_GT. Hôm nay bạn cần hỗ trợ gì về cấu trúc dữ liệu hoặc sửa lỗi code?"}]
                                st.rerun()
                            else:
                                st.error(f"❌ Mã sinh viên '{input_mssv}' không tồn tại!")
                        except Exception as e:
                            st.error(f"❌ Lỗi kết nối máy chủ dữ liệu: {e}")
    st.stop()

# ============================================================
# GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP THÀNH CÔNG
# ============================================================
current_user = st.session_state.authenticated_mssv
col_workspace, col_chatbot = st.columns([6, 4], gap="large")

with col_workspace:
    st.markdown("### KHOA CNTT")
    st.caption("Cấu trúc dữ liệu & Giải thuật")
    st.info(f"👤 Tài khoản: **{current_user}** | Vai trò: Sinh Viên Chính Thức")
    
    nav1, nav2, nav3, nav_out = st.columns([1.2, 1.6, 1.3, 1.2])
    if nav1.button("🏠 Trang Chủ", use_container_width=True): st.session_state.current_page = "home"
    if nav2.button("📚 Tài Liệu Bài Học", use_container_width=True): st.session_state.current_page = "lessons"
    if nav3.button("🔔 Nộp Bài Tập", use_container_width=True): st.session_state.current_page = "news"
    
    if nav_out.button("🚪 Đăng Xuất", use_container_width=True, type="secondary"):
        st.session_state.authenticated_mssv = None
        st.session_state.messages = []
        st.session_state.current_page = "home"
        st.rerun()
        
    st.markdown("---")

    if st.session_state.current_page == "home":
        st.markdown(f"## DSA-Learning: Hệ Thống Học Tập Số")
        st.markdown(f"Chào mừng sinh viên **{current_user}** đến với hệ thống học liệu điện tử chuyên ngành.")
        
        # Đã Xóa phần Bảng thông báo theo yêu cầu

        grid_col1, grid_col2 = st.columns(2)
        with grid_col1:
            st.markdown("""
            <div class='topic-card'>
                <div class='topic-title'>📖 Tài liệu số hóa</div>
                <p style='color:#475569; font-size:0.9rem;'>Toàn bộ 6 chương giáo trình cốt lõi đã được tối ưu hóa hiển thị. Sinh viên có thể đọc nhanh tóm tắt hoặc tải file chi tiết.</p>
            </div>
            """, unsafe_allow_html=True)
        with grid_col2:
            st.markdown("""
            <div class='topic-card'>
                <div class='topic-title'>🤖 Trợ lý ảo DSA Assistant</div>
                <p style='color:#475569; font-size:0.9rem;'>Hệ thống AI chuyên biệt sẵn sàng phân tích, phát hiện bug logic trong mã nguồn và giải đáp lý thuyết thuật toán 24/7.</p>
            </div>
            """, unsafe_allow_html=True)

    elif st.session_state.current_page == "lessons":
        st.markdown("### 📚 Danh sách các chương học phần")
        list_chapters = [f"Chương {i}: {CHAPTER_DATA[i]['title'].split(': ')[1]}" for i in range(1, 7)]
        selected_option = st.selectbox("Chọn chương học cần nghiên cứu:", list_chapters)
        ch_num = list_chapters.index(selected_option) + 1
        ch_info = CHAPTER_DATA[ch_num]
        
        st.markdown(f"## {ch_info['title']}")
        st.write(ch_info['desc'])
        st.link_button("📂 Mở giáo trình Google Doc chi tiết", ch_info['pdf'], type="primary")
        
        st.markdown("#### 💡 Kiến thức trọng tâm gồm:")
        for topic in ch_info['topics']:
            st.markdown(f"<div class='topic-card'><div class='topic-title'>▪️ {topic['name']}</div><p style='color:#475569; font-size:0.95rem; margin:0;'>{topic['detail']}</p></div>", unsafe_allow_html=True)

    elif st.session_state.current_page == "news":
        st.markdown("## 🔔 Hệ Thống Nộp Bài Tập")
        st.write("Sinh viên lưu ý lựa chọn đúng khối đào tạo của mình để nộp bài tập thực hành hàng tuần về đúng lớp Google Classroom.")
        
        class_col1, class_col2 = st.columns(2)
        with class_col1:
            with st.container(border=True):
                st.markdown("<h3 style='color: #3b82f6;'>🟦 Hệ Cao Đẳng</h3>", unsafe_allow_html=True)
                st.write("Yêu cầu nộp đầy đủ file báo cáo (.docx) kèm tệp mã nguồn (.cpp).")
                st.link_button("VÀO GOOGLE CLASSROOM", "https://classroom.google.com/c/ODQ3NzA2MTY2Mjc2?cjc=wnxa7x6m", use_container_width=True)
                
        with class_col2:
            with st.container(border=True):
                st.markdown("<h3 style='color: #f59e0b;'>🟨 Hệ Trung Cấp</h3>", unsafe_allow_html=True)
                st.write("Yêu cầu hoàn thành bài tập trắc nghiệm lý thuyết và chụp ảnh màn hình.")
                st.link_button("VÀO GOOGLE CLASSROOM", "https://classroom.google.com/c/ODQ3NzA2MTY2Mjc2?cjc=wnxa7x6m", use_container_width=True)

with col_chatbot:
    st.markdown("### 🤖 Trợ lý ảo DSA Assistant")
    st.caption("Tôi ở đây để giúp bạn hiểu rõ bản chất của thuật toán.")
    st.markdown("---")
    
    chat_container = st.container(height=450)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    if prompt := st.chat_input("Nhập câu hỏi lý thuyết hoặc dán mã nguồn cần sửa lỗi..."):
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("assistant"):
                try:
                    res = st.session_state.rag_chain.query(prompt)
                    ans = res.get("answer", "Hệ thống trục trặc, không có phản hồi.")
                    sources = res.get("sources", [])
                    
                    def stream_generator():
                        for word in ans.split(" "):
                            yield word + " "
                            time.sleep(0.02)
                    st.write_stream(stream_generator)
                    
                    if sources:
                        st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
                        
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    threading.Thread(target=ghi_log_realtime, args=(current_user, prompt, ans)).start()
                    st.rerun()
                except Exception as e:
                    err = f"❌ Hệ thống đang quá tải. Xin vui lòng đợi ít giây và nhấn thử lại! (Lỗi: {e})"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})