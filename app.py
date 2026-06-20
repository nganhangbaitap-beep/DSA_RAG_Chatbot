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

# Cấu hình hiển thị trang chính của Streamlit
st.set_page_config(page_title="DSA Learning System", page_icon="📚", layout="wide")

# ============================================================
# TÁI THIẾT KẾ TOÀN DIỆN GIAO DIỆN (ADVANCED CSS INJECTION)
# ============================================================
st.markdown("""
<style>
    /* Cấu hình phông chữ và nền tảng giao diện sạch sẽ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc !important;
    }
    
    /* Ẩn bớt các khoảng trắng mặc định thừa thãi của Streamlit */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        max-width: 1200px !important;
    }
    
    /* Thiết kế Thanh điều hướng & Header cao cấp */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    /* Thẻ hiển thị nội dung bài học (Topic Cards) */
    .lesson-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        transition: all 0.25s ease;
    }
    .lesson-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        border-color: #10a37f;
    }
    .lesson-badge {
        background-color: #e6f7f0;
        color: #10a37f;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 12px;
    }
    
    /* ========================================================
       CẤU HÌNH BIỂU TƯỢNG BONG BÓNG CHAT NỔI (FLOATING CHATBOT)
       ======================================================== */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 35px;
        right: 35px;
        z-index: 99999;
    }
    
    /* Định hình nút bấm Chat tròn trịa như ứng dụng Messenger */
    div[data-testid="stPopover"] button {
        background: linear-gradient(135deg, #10a37f 0%, #0d8567 100%) !important;
        color: white !important;
        border-radius: 30px !important;
        padding: 14px 24px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0 10px 25px -5px rgba(16, 163, 127, 0.5) !important;
        border: none !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stPopover"] button:hover {
        transform: scale(1.04);
        box-shadow: 0 15px 30px -5px rgba(16, 163, 127, 0.7) !important;
    }
    
    /* Định dạng hộp thoại khung Chat khi bung lên rộng rãi, trực quan */
    div[data-testid="stPopoverWindow"] {
        width: 380px !important;
        max-height: 520px !important;
        background-color: #ffffff !important;
        border-radius: 20px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
        border: 1px solid #f1f5f9 !important;
        padding: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CƠ SỞ DỮ LIỆU ĐỒNG BỘ NỘI DUNG 6 CHƯƠNG GIÁO TRÌNH
# ============================================================
CHAPTER_DATA = {
    1: {
        "title": "Chương 1: Thiết kế và phân tích giải thuật",
        "desc": "Phương pháp đánh giá hiệu suất, thời gian chạy và tối ưu cấu trúc thuật toán tổng quát.",
        "pdf": "https://docs.google.com/document/d/1WC2VmOU_jhVfGzH_mPsQhozCDDXSFCbfpHYIBfULr2o/edit",
        "topics": [
            {"name": "Độ phức tạp thuật toán", "detail": "Phân tích cú pháp tính toán thời gian, không gian và ý nghĩa thực tế ký pháp Big O."},
            {"name": "Chiến lược thiết kế giải thuật", "detail": "Tìm hiểu các mô hình kinh điển: Chia để trị, Tham lam, Quy hoạch động."}
        ]
    },
    2: {
        "title": "Chương 2: Các kiểu dữ liệu cơ sở",
        "desc": "Hệ thống hóa các kiểu dữ liệu nền tảng cấu thành cấu trúc kiến trúc lớn.",
        "pdf": "https://docs.google.com/document/d/1eky8_mvFQfTl8kvt3pg9fDeR5Hhq1jsEz5RQrWVt7-M/edit",
        "topics": [
            {"name": "Kiểu dữ liệu trừu tượng", "detail": "Định nghĩa tổng quan và tầm quan trọng của mô hình ADT trong cấu trúc dữ liệu."},
            {"name": "Con trỏ & Quản lý bộ nhớ", "detail": "Cơ chế hoạt động của biến con trỏ, tham chiếu và cấp phát động vùng nhớ."}
        ]
    },
    3: {
        "title": "Chương 3: Mảng, danh sách",
        "desc": "Tổ chức và quản lý cấu trúc các kiến trúc dữ liệu dạng tuyến tính tuần tự.",
        "pdf": "https://docs.google.com/document/d/1W845YWZlPpKLogb_ECmsXSQoMqcrpfh4IhuZ-Xv7tZA/edit",
        "topics": [
            {"name": "Cấu trúc Danh sách liên kết", "detail": "So sánh Mảng tĩnh với cấu trúc Danh sách liên kết đơn, danh sách liên kết đôi."},
            {"name": "Ngăn xếp & Hàng đợi", "detail": "Nguyên lý hoạt động và ứng dụng thực tế cấu trúc LIFO (Stack) và FIFO (Queue)."}
        ]
    },
    4: {
        "title": "Chương 4: Cây (Tree)",
        "desc": "Cấu trúc dữ liệu phân cấp dạng phi tuyến tính.",
        "pdf": "https://docs.google.com/document/d/1j39PD2vDIkuzNDe6FK_AntIUSlUjttELZmeWXANeO1k/edit",
        "topics": [
            {"name": "Cây nhị phân và các phép duyệt", "detail": "Các giải thuật duyệt cây phổ biến hệ thống: Tiền tự, Trung tự, Hậu tự."},
            {"name": "Cây tìm kiếm nhị phân (BST)", "detail": "Ứng dụng cấu trúc cây nhị phân tăng tốc độ tìm kiếm và tối ưu chèn phần tử."}
        ]
    },
    5: {
        "title": "Chương 5: Sắp xếp (Sorting)",
        "desc": "Các kỹ thuật hoán đổi vị trí và chuẩn hóa sắp xếp dãy dữ liệu thô.",
        "pdf": "https://docs.google.com/document/d/1jDSv-XYq1l0iwsA-T-P9aFZy6nSn9zbMwjplUAewsoo/edit",
        "topics": [
            {"name": "Các thuật toán sắp xếp đơn giản", "detail": "Phân tích mã nguồn giải thuật: Sắp xếp đổi chỗ, Sắp xếp chèn, Sắp xếp lựa chọn."},
            {"name": "Các giải thuật nâng cao hiệu suất", "detail": "Cách thức vận hành chiến lược chia để trị nâng cao qua Quick Sort và Merge Sort."}
        ]
    },
    6: {
        "title": "Chương 6: Tìm kiếm (Searching)",
        "desc": "Truy xuất thông tin tối ưu trên mảng và danh sách dữ liệu.",
        "pdf": "https://docs.google.com/document/d/1txFeyednVsiMHqkbvG3WuHn4GejBETI_QaD24w1rxYY/edit",
        "topics": [
            {"name": "Tìm kiếm tuyến tính", "detail": "Giải pháp tìm kiếm áp dụng cho tập danh sách thô chưa có thứ tự sắp xếp."},
            {"name": "Tìm kiếm nhị phân", "detail": "Giải thuật tối ưu tốc độ áp dụng trên danh sách mảng dữ liệu đã được sắp xếp."}
        ]
    }
}

# ============================================================
# HÀM KẾT NỐI SHEETS VÀ LƯU LOG TRỰC TUYẾN (BỘ LỌC CHẶN CÂU CHÀO)
# ============================================================
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "GOOGLE_CREDS_JSON" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        if not os.path.exists("google_creds.json"):
            st.error("❌ Thiếu file google_creds.json để kết nối dữ liệu!")
            st.stop()
        creds = Credentials.from_service_account_file("google_creds.json", scopes=scopes)
    return gspread.authorize(creds).open(GOOGLE_SHEET_NAME)

def ghi_log_realtime(mssv, cau_hoi, cau_tra_loi):
    text_lower = cau_hoi.strip().lower()
    
    # 1. Bộ màng lọc chặn vĩnh viễn các câu chào hỏi từ sinh viên
    black_list = ["xin chào", "chào", "chào bạn", "hello", "hi", "alo", "test", "bot"]
    if text_lower in black_list: 
        return
        
    # 2. Bộ lọc chặn lời chào hệ thống tự động từ AI trợ lý
    if "Tôi là trợ lý học tập" in cau_tra_loi or "Tôi là trợ lý ảo chuyên trách" in cau_tra_loi:
        return
        
    # 3. Chặn ghi các câu nhập thử nghiệm quá ngắn
    if len(text_lower) <= 5: 
        return
        
    clean_question = cau_hoi.strip().replace("\n", " ➔ ")
    thoi_gian_vn = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")
    try:
        wks = get_google_sheet().worksheet(TAB_LICH_SU)
        wks.insert_rows([[mssv, thoi_gian_vn, clean_question]], row=len(wks.col_values(1)) + 1) 
    except Exception as e: 
        print(f"Log lỗi Sheets: {e}")

# ============================================================
# KHỞI TẠO BỘ NHỚ BIẾN SESSION STATE VÀ KHUNG AI RAG CHATBOT
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
# MÀN HÌNH XÁC THỰC TRUY CẬP (LOGIN)
# ============================================================
if not st.session_state.authenticated_mssv:
    _, login_col, _ = st.columns([1, 1.8, 1])
    with login_col:
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom:0;'>📚</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #0f172a; margin-top:10px; font-weight:700;'>DSA Learning System</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom:30px; font-size:0.95rem;'>Hệ Thống Số Hóa Học Liệu Chuyên Ngành — Khoa CNTT</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            input_mssv = st.text_input("MÃ SỐ SINH VIÊN CHÍNH THỨC:", placeholder="Nhập Mã Số SV (Ví dụ: SV01)").strip().upper()
            submit_btn = st.form_submit_button("XÁC THỰC VÀO LỚP HỌC", use_container_width=True)
            
            if submit_btn:
                if not input_mssv:
                    st.error("⚠ Vui lòng cung cấp Mã số sinh viên hợp lệ!")
                elif input_mssv == "ADMIN":
                    st.session_state.authenticated_mssv = "ADMIN"
                    st.session_state.messages = [{"role": "assistant", "content": "Xin chào Quản trị viên! Bạn vừa truy cập thành công phòng điều khiển."}]
                    st.rerun()
                else:
                    with st.spinner("Đang kiểm tra danh sách lớp..."):
                        try:
                            wks = get_google_sheet().worksheet(TAB_DANH_SACH)
                            valid_students = [str(x).strip().upper() for x in wks.col_values(1)]
                            
                            if input_mssv in valid_students:
                                st.session_state.authenticated_mssv = input_mssv
                                st.session_state.messages = [{"role": "assistant", "content": f"Chào bạn **{input_mssv}**! Tôi là trợ lý học tập môn CTDL_GT. Hôm nay bạn cần hỗ trợ gì về cấu trúc dữ liệu hoặc sửa lỗi code?"}]
                                st.rerun()
                            else:
                                st.error(f"❌ Mã sinh viên '{input_mssv}' không thuộc danh sách lớp!")
                        except Exception as e:
                            st.error(f"❌ Lỗi kết nối hệ thống dữ liệu: {e}")
    st.stop()

# ============================================================
# KHÔNG GIAN LÀM VIỆC CHÍNH (FULL-WIDTH DASHBOARD WORKSPACE)
# ============================================================
current_user = st.session_state.authenticated_mssv

# Thanh Tiêu Đề Dashboard Hiện Đại
st.markdown(f"""
<div class='main-header'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h2 style='margin:0; font-weight:700; color:white; font-size:1.6rem;'>Hệ Thống Học Liệu Điện Tử Số Hóa</h2>
            <p style='margin:5px 0 0 0; color:#94a3b8; font-size:0.9rem;'>Học phần: Cấu trúc dữ liệu & Giải thuật | Khoa Công nghệ thông tin</p>
        </div>
        <div style='text-align: right; background: rgba(255,255,255,0.07); padding: 8px 16px; border-radius: 10px;'>
            <span style='color:#cbd5e1; font-size:0.85rem; display:block;'>Tài khoản đăng nhập</span>
            <strong style='color:#10a37f; font-size:1rem;'>👤 {current_user}</strong>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Thanh Điều Hướng Dạng Nút Bấm Đẹp
nav1, nav2, nav3, nav_out = st.columns([1, 1, 1, 0.8])
if nav1.button("🏠 Trang Chủ Hệ Thống", use_container_width=True): st.session_state.current_page = "home"
if nav2.button("📚 Học Liệu Giáo Trình", use_container_width=True): st.session_state.current_page = "lessons"
if nav3.button("🔔 Nộp Bài Thực Hành", use_container_width=True): st.session_state.current_page = "news"

if nav_out.button("🚪 Đăng Xuất", use_container_width=True, type="secondary"):
    st.session_state.authenticated_mssv = None
    st.session_state.messages = []
    st.session_state.current_page = "home"
    st.rerun()
    
st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# --- PHÂN PHỐI NỘI DUNG THEO TỪNG TAB TRANG CHỨC NĂNG ---
if st.session_state.current_page == "home":
    st.markdown(f"### Chào mừng quay trở lại, sinh viên {current_user} 👋")
    st.markdown("Lựa chọn các mục lục trên thanh điều hướng để tải tài liệu giáo trình hoặc xem thông tin nộp bài tập thực hành.")
    
    grid_col1, grid_col2 = st.columns(2, gap="medium")
    with grid_col1:
        st.markdown("""
        <div class='lesson-card'>
            <span class='lesson-badge'>HỌC LIỆU CHÍNH THỨC</span>
            <h4 class='topic-title' style='margin-top:0;'>📖 Giáo trình 6 chương cốt lõi</h4>
            <p style='color:#475569; font-size:0.9rem; line-height:1.5;'>Nội dung bài học được biên soạn chi tiết, tích hợp liên kết trực tiếp tới tài liệu Google Docs trực tuyến giúp xem nhanh và thực hành code tiện lợi.</p>
        </div>
        """, unsafe_allow_html=True)
    with grid_col2:
        st.markdown("""
        <div class='lesson-card'>
            <span class='lesson-badge'>AI ASSISTANT</span>
            <h4 class='topic-title' style='margin-top:0;'>🤖 Trợ lý ảo DSA thông minh</h4>
            <p style='color:#475569; font-size:0.9rem; line-height:1.5;'>Sử dụng biểu tượng chat luôn hiển thị ở <b>góc dưới bên phải màn hình</b> để trò chuyện trực tiếp, phân tích cấu trúc lỗi logic hoặc sửa lỗi mã nguồn lập trình 24/7.</p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "lessons":
    st.markdown("### 📚 Danh mục các chương giáo trình đào tạo")
    list_chapters = [f"Chương {i}: {CHAPTER_DATA[i]['title'].split(': ')[1]}" for i in range(1, 7)]
    selected_option = st.selectbox("Lựa chọn chương học cần nghiên cứu dữ liệu cấu trúc:", list_chapters)
    ch_num = list_chapters.index(selected_option) + 1
    ch_info = CHAPTER_DATA[ch_num]
    
    st.markdown(f"## {ch_info['title']}")
    st.write(ch_info['desc'])
    st.link_button("📂 Mở tệp giáo trình chi tiết (Google Docs)", ch_info['pdf'], type="primary")
    
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 💡 Các kiến thức cốt lõi trọng tâm cần nắm vững:")
    for topic in ch_info['topics']:
        st.markdown(f"""
        <div class='lesson-card'>
            <div class='topic-title'>▪️ {topic['name']}</div>
            <p style='color:#475569; font-size:0.95rem; margin:8px 0 0 0; line-height:1.5;'>{topic['detail']}</p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "news":
    st.markdown("## 🔔 Cổng nộp bài thực hành trực tuyến")
    st.write("Vui lòng lựa chọn chính xác hệ đào tạo tương ứng để nộp bài tập về đúng phân lớp Google Classroom.")
    
    class_col1, class_col2 = st.columns(2, gap="medium")
    with class_col1:
        with st.container(border=True):
            st.markdown("<h3 style='color: #3b82f6; font-weight:600; margin-top:0;'>🟦 Khối Cao Đẳng</h3>", unsafe_allow_html=True)
            st.write("Yêu cầu hoàn thiện tệp tài liệu báo cáo phân tích thuật toán (.docx) kèm các file mã nguồn chương trình mở rộng (.cpp).")
            st.link_button("VÀO LỚP GOOGLE CLASSROOM", "https://classroom.google.com/c/ODQ3NzA2MTY2Mjc2?cjc=wnxa7x6m", use_container_width=True)
            
    with class_col2:
        with st.container(border=True):
            st.markdown("<h3 style='color: #f59e0b; font-weight:600; margin-top:0;'>🟨 Khối Trung Cấp</h3>", unsafe_allow_html=True)
            st.write("Yêu cầu hoàn thành bài thi trắc nghiệm đánh giá lý thuyết giải thuật định kỳ và tải lên hình ảnh kết quả xác thực lớp học.")
            st.link_button("VÀO LỚP GOOGLE CLASSROOM", "https://classroom.google.com/c/ODQ3NzA2MTY2Mjc2?cjc=wnxa7x6m", use_container_width=True)

# ============================================================
# TẠO BONG BÓNG CHAT CHATBOT NỔI GÓC DƯỚI BÊN PHẢI (ST.POPOVER)
# ============================================================
with st.popover("💬 Trợ lý DSA"):
    st.markdown("<h4 style='margin:0; color:#10a37f; font-weight:700;'>🤖 DSA Assistant</h4>", unsafe_allow_html=True)
    st.caption("Trợ lý ảo phân tích giải thuật và sửa lỗi code chuyên trách.")
    st.markdown("---")
    
    # Khung cửa sổ cuộn nội dung tin nhắn chat
    chat_container = st.container(height=340)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    # Ô nhập liệu tin nhắn gán ở đáy khung popover nổi
    if prompt := st.chat_input("Hỏi lý thuyết giải thuật hoặc dán code cần debug..."):
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
                    
                    # Hiệu ứng gõ chữ trực quan, sinh động
                    def stream_generator():
                        for word in ans.split(" "):
                            yield word + " "
                            time.sleep(0.015)
                    st.write_stream(stream_generator)
                    
                    if sources:
                        st.caption(f"📄 Tài liệu tham khảo: {', '.join(sources)}")
                        
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    
                    # Gọi tiến trình ngầm kiểm tra điều kiện và thực hiện ghi log lên Sheets
                    threading.Thread(target=ghi_log_realtime, args=(current_user, prompt, ans)).start()
                except Exception as e:
                    err = f"❌ Máy chủ phản hồi chậm. Xin vui lòng thử lại! (Chi tiết lỗi: {e})"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})