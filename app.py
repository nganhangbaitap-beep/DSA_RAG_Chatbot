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
# TÁI THIẾT KẾ TOÀN DIỆN GIAO DIỆN (SIDEBAR STYLE & HIDE RUNNING)
# ============================================================
st.markdown("""
<style>
    /* Cấu hình phông chữ nền tảng hệ thống */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc !important;
    }
    
    /* 1. ẨN BIỂU TƯỢNG CHẠY RUNNING/LOADING TRÊN THANH TASK TOP-RIGHT */
    div[data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Làm gọn không gian hiển thị nội dung chính */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* Thiết kế tiêu đề trang chính */
    .content-header {
        background-color: #ffffff;
        padding: 20px 25px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Thẻ hiển thị nội dung bài học (Lesson Cards) */
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
    .topic-title {
        color: #0f172a !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
    }
    
    /* Ẩn menu mặc định của Streamlit */
    div[data-testid="stSidebarNav"] {display: none;} 
    
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
# CƠ SỞ DỮ LIỆU ĐỒNG BỘ NỘI DUNG 6 CHƯƠNG GIÁO TRÌNH (TINH GỌN)
# ============================================================
CHAPTER_DATA = {
    1: {
        "title": "Chương 1: Thiết kế & phân tích giải thuật",
        "desc": "Đánh giá hiệu suất thuật toán qua thời gian chạy, không gian bộ nhớ và các chiến lược thiết kế tổng quát.",
        "pdf": "https://docs.google.com/document/d/1WC2VmOU_jhVfGzH_mPsQhozCDDXSFCbfpHYIBfULr2o/edit",
        "topics": [
            {"name": "Độ phức tạp thuật toán", "detail": "Big O, cách xác định và so sánh. Phân tích time/space"},
            {"name": "Chiến lược thiết kế", "detail": "Nguyên lý giải quyết bài toán bằng phương pháp Chia để trị, Tham lam, Quy hoạch động."}
        ]
    },
    2: {
        "title": "Chương 2: Các kiểu dữ liệu cơ sở",
        "desc": "Tìm hiểu kiểu dữ liệu trừu tượng, cơ chế biến con trỏ và quản lý bộ nhớ trong lập trình.",
        "pdf": "https://docs.google.com/document/d/1eky8_mvFQfTl8kvt3pg9fDeR5Hhq1jsEz5RQrWVt7-M/edit",
        "topics": [
            {"name": "Kiểu dữ liệu trừu tượng", "detail": "Khái niệm và cách định nghĩa mô hình dữ liệu trừu tượng (ADT)."},
            {"name": "Con trỏ và bộ nhớ", "detail": "Cơ chế hoạt động của con trỏ và kỹ thuật quản lý, cấp phát bộ nhớ động."}
        ]
    },
    3: {
        "title": "Chương 3: Mảng và danh sách",
        "desc": "Tổ chức, quản lý và thao tác dữ liệu trên các cấu trúc tuyến tính (tuần tự).",
        "pdf": "https://docs.google.com/document/d/1W845YWZlPpKLogb_ECmsXSQoMqcrpfh4IhuZ-Xv7tZA/edit",
        "topics": [
            {"name": "Mảng & Danh sách liên kết", "detail": "Cách tổ chức, vận hành dữ liệu trên cấu trúc mảng, danh sách liên kết."},
            {"name": "Stack & Queue", "detail": "Nguyên lý hoạt động và ứng dụng của Ngăn xếp (LIFO) và Hàng đợi (FIFO)."}
        ]
    },
    4: {
        "title": "Chương 4: Cây (Tree)",
        "desc": "Tổ chức dữ liệu theo mô hình phân cấp phi tuyến tính.",
        "pdf": "https://docs.google.com/document/d/1j39PD2vDIkuzNDe6FK_AntIUSlUjttELZmeWXANeO1k/edit",
        "topics": [
            {"name": "Cây nhị phân và duyệt cây", "detail": "Cấu trúc cây nhị phân và các giải thuật duyệt cây: Preorder, Inorder, Postorder."},
            {"name": "Cây tìm kiếm nhị phân", "detail": "Đặc điểm đặc trưng của cấu trúc BST cùng các thao tác chèn, xóa và tra cứu."}
        ]
    },
    5: {
        "title": "Chương 5: Sắp xếp (Sorting)",
        "desc": "Các thuật toán tổ chức và sắp xếp thứ tự các phần tử trong dãy dữ liệu.",
        "pdf": "https://docs.google.com/document/d/1jDSv-XYq1l0iwsA-T-P9aFZy6nSn9zbMwjplUAewsoo/edit",
        "topics": [
            {"name": "Thuật toán cơ bản", "detail": "Nguyên lý vận hành các giải thuật sắp xếp: Bubble Sort, Insertion Sort, Selection Sort."},
            {"name": "Thuật toán nâng cao", "detail": "Cơ chế tối ưu hóa thời gian xử lý dữ liệu quy mô lớn qua Quick Sort và Merge Sort."}
        ]
    },
    6: {
        "title": "Chương 6: Tìm kiếm (Searching)",
        "desc": "Các kỹ thuật tra cứu và truy xuất thông tin tối ưu trên cấu trúc dữ liệu.",
        "pdf": "https://docs.google.com/document/d/1txFeyednVsiMHqkbvG3WuHn4GejBETI_QaD24w1rxYY/edit",
        "topics": [
            {"name": "Tìm kiếm tuyến tính", "detail": "Thuật toán quét tuần tự áp dụng cho tập dữ liệu thô chưa qua sắp xếp."},
            {"name": "Tìm kiếm nhị phân", "detail": "Kỹ thuật chia đôi phạm vi tra cứu, tối ưu tốc độ trên dãy dữ liệu đã có thứ tự."}
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
# CẤU HÌNH SIDEBAR MENU BÊN TRÁI ĐÚNG THEO SƠ ĐỒ MỚI
# ============================================================
current_user = st.session_state.authenticated_mssv

with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 15px 0 10px 0;'>
        <h1 style='font-size: 2.8rem; margin:0;'>📚</h1>
        <h3 style='color: #0f172a; margin-top:8px; font-weight:700; font-size:1.25rem;'>DSA Learning</h3>
        <p style='color: #64748b; font-size:0.85rem; margin-bottom:20px;'>Khoa Công nghệ thông tin</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Khung hiển thị thông tin sinh viên đăng nhập dạng thẻ (Card)
    st.markdown(f"""
    <div style='background-color: #ffffff; padding: 12px 16px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 10px;'>
        <span style='color:#64748b; font-size:0.75rem; display:block; font-weight:500;'>TÀI KHOẢN SINH VIÊN</span>
        <strong style='color:#10a37f; font-size:0.95rem;'>👤 {current_user}</strong>
        <span style='background-color: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; display: inline-block; margin-top: 5px;'>Chính thức</span>
    </div>
    """, unsafe_allow_html=True)
    
    # NÚT ĐĂNG XUẤT ĐÃ ĐƯỢC CHUYỂN LÊN ĐÂY (NGAY DƯỚI TÀI KHOẢN SINH VIÊN)
    if st.button("🚪 Đăng Xuất", use_container_width=True, type="secondary"):
        st.session_state.authenticated_mssv = None
        st.session_state.messages = []
        st.session_state.current_page = "home"
        st.rerun()
        
    st.markdown("<div style='margin-bottom: 30px; border-bottom: 1px solid #e2e8f0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.75rem; font-weight:700; margin-left: 5px; margin-bottom: 8px;'>DANH MỤC HỆ THỐNG</p>", unsafe_allow_html=True)
    
    # Bộ nút bấm chuyển đổi giữa các Tab chức năng nội dung
    if st.button("🏠 Trang Chủ Hệ Thống", use_container_width=True, type="primary" if st.session_state.current_page == "home" else "secondary"):
        st.session_state.current_page = "home"
        st.rerun()
        
    if st.button("📚 Học Liệu Giáo Trình", use_container_width=True, type="primary" if st.session_state.current_page == "lessons" else "secondary"):
        st.session_state.current_page = "lessons"
        st.rerun()
        
    if st.button("🔔 Nộp Bài Thực Hành", use_container_width=True, type="primary" if st.session_state.current_page == "news" else "secondary"):
        st.session_state.current_page = "news"
        st.rerun()

# ============================================================
# KHÔNG GIAN HIỂN THỊ NỘI DUNG CHÍNH (MAIN CONTENT AREA)
# ============================================================

# Khung tiêu đề tĩnh cho vùng nội dung chính
st.markdown(f"""
<div class='content-header'>
    <h2 style='margin:0; font-weight:700; color:#0f172a; font-size:1.4rem;'>Học Liệu Điện Tử Số Hóa Chuyên Ngành</h2>
    <p style='margin:4px 0 0 0; color:#64748b; font-size:0.85rem;'>Môn học: Cấu trúc dữ liệu và Giải thuật (DSA)</p>
</div>
""", unsafe_allow_html=True)

# --- XỬ LÝ ĐỔI NỘI DUNG THEO TAB ĐANG CHỌN Ở SIDEBAR ---
if st.session_state.current_page == "home":
    st.markdown(f"### Chào mừng bạn quay trở lại học tập, sinh viên {current_user} 👋")
    st.markdown("Sử dụng các tab danh mục ở **Thanh điều hướng bên trái** để mở các chương tài liệu giáo trình hoặc truy cập cổng nộp bài tập Classroom.")
    
    grid_col1, grid_col2 = st.columns(2, gap="medium")
    with grid_col1:
        st.markdown("""
        <div class='lesson-card'>
            <span class='lesson-badge'>KHO TÀI LIỆU SỐ</span>
            <h4 class='topic-title'>📖 Giáo trình 6 chương cốt lõi</h4>
            <p style='color:#475569; font-size:0.9rem; line-height:1.5;'>Học phần trực quan hóa cấu trúc dữ liệu được liên kết đồng bộ trực tiếp với Google Docs trực tuyến giúp bạn đọc nhanh, tra cứu thuật toán mượt mà.</p>
        </div>
        """, unsafe_allow_html=True)
    with grid_col2:
        st.markdown("""
        <div class='lesson-card'>
            <span class='lesson-badge'>TRỢ LÝ THUẬT TOÁN</span>
            <h4 class='topic-title'>🤖 Trợ lý ảo DSA thông minh</h4>
            <p style='color:#475569; font-size:0.9rem; line-height:1.5;'>Nhấp vào biểu tượng bong bóng chat luôn cố định ở <b>góc dưới bên phải màn hình</b> để hỏi lý thuyết giải thuật hoặc paste mã nguồn nhờ AI sửa lỗi logic 24/7.</p>
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
            <div class='topic-title' style='color:#10a37f !important;'>▪️ {topic['name']}</div>
            <p style='color:#475569; font-size:0.95rem; margin:8px 0 0 0; line-height:1.5;'>{topic['detail']}</p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "news":
    st.markdown("## 🔔 Cổng nộp bài thực hành trực tuyến")
    st.write("Sinh viên lưu ý lựa chọn chính xác khối đào tạo tương ứng để nộp bài tập về đúng phân lớp Google Classroom.")
    
    class_col1, class_col2 = st.columns(2, gap="medium")
    with class_col1:
        with st.container(border=True):
            st.markdown("<h3 style='color: #3b82f6; font-weight:600; margin-top:0;'>🟦 Khối Cao Đẳng</h3>", unsafe_allow_html=True)
            st.write("Nộp bài tập thực hành tại Classroom của lớp học")
            st.link_button("VÀO LỚP GOOGLE CLASSROOM", "https://classroom.google.com/c/ODQ3NzA2MTY2Mjc2?cjc=wnxa7x6m", use_container_width=True)
            
    with class_col2:
        with st.container(border=True):
            st.markdown("<h3 style='color: #f59e0b; font-weight:600; margin-top:0;'>🟨 Khối Trung Cấp</h3>", unsafe_allow_html=True)
            st.write("Nộp bài tập thực hành tại Classroom của lớp học")
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

