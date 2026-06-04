# -*- coding: utf-8 -*-
# ingest.py — Nạp tài liệu vào Vector Store (Stable - Anti 429)

import os
import sys
import shutil
import argparse
import time
import random
from pathlib import Path

from loaders import load_pdf, load_pdf_ocr, load_word, load_website
from core import split_documents, GeminiEmbedder, VectorStore
from config import CHROMA_PERSIST_DIR


# ============================================================
# CONFIG (ĐÃ TỐI ƯU CHO GEMINI FREE TIER - ANTI 429)
# ============================================================
BATCH_SIZE = 128            # Tăng mạnh từ 5 lên 128 để tận dụng tối đa tính toán song song cục bộ
BASE_SLEEP = 0.0            # Đưa thời gian chờ về 0.0 giây (Không lo dính lỗi nghẽn API Rate Limit 429)
MAX_RETRY = 1               # Giảm tối đa số lần retry vì chạy cục bộ hiếm khi sập kết nối
BACKOFF_BASE = 1

# =========================
# LOADERS
# =========================
def ingest_file(file_path: str, use_ocr: bool = False) -> list:
    path = Path(file_path)
    if not path.exists():
        print(f"File khong ton tai: {file_path}")
        return []

    ext = path.suffix.lower()

    if ext == ".pdf":
        if use_ocr:
            docs = load_pdf_ocr(file_path)
        else:
            docs = load_pdf(file_path)
            if not docs or all(len(d.page_content) < 50 for d in docs):
                print("   --> PDF it text, thu OCR...")
                docs = load_pdf_ocr(file_path)

    elif ext in [".docx", ".doc"]:
        docs = load_word(file_path)

    else:
        print(f"Dinh dang khong ho tro: {ext}")
        return []

    return docs if isinstance(docs, list) else []


def ingest_directory(dir_path: str, use_ocr: bool = False) -> list:
    all_docs = []
    supported = [".pdf", ".docx", ".doc"]

    dir_path = Path(dir_path)
    files = [f for f in dir_path.rglob("*") if f.suffix.lower() in supported]

    print(f"\nTim thay {len(files)} file trong {dir_path}")

    for i, file in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file.name}")
        all_docs.extend(ingest_file(str(file), use_ocr))

    return all_docs


# =========================
# BACKOFF
# =========================
def backoff_sleep(attempt):
    # Lần 1: ~4s | Lần 2: ~10s | Lần 3: ~28s | Lần 4: ~82s (đủ thời gian để gỡ block Quota)
    delay = (BACKOFF_BASE ** (attempt + 1)) + random.uniform(1.0, 3.0)
    print(f"   [429 Quota] Tạm nghỉ {delay:.1f}s trước khi thử lại (Lần thử {attempt+1}/{MAX_RETRY})...")
    time.sleep(delay)


# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser(description="Nap tai lieu vao RAG Chatbot DSA")
    parser.add_argument("--file",  type=str)
    parser.add_argument("--dir",  type=str)
    parser.add_argument("--url",  type=str)
    parser.add_argument("--ocr",  action="store_true")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()

    if not any([args.file, args.dir, args.url]):
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print("RAG Chatbot DSA - Nap Tai Lieu")
    print("=" * 60)

    # clear DB
    if args.clear and os.path.exists(CHROMA_PERSIST_DIR):
        print(f"\nXoa database cu: {CHROMA_PERSIST_DIR}")
        try:
            shutil.rmtree(CHROMA_PERSIST_DIR)
            print("[OK] Da xoa")
        except PermissionError:
            print("[!] Khong the xoa DB (dang bi khoa)")
            sys.exit(1)

    # init
    try:
        embedder = GeminiEmbedder()
        vs = VectorStore(embedder)
    except Exception as e:
        print(f"Loi khoi tao: {e}")
        sys.exit(1)

    # collect docs
    all_docs = []

    if args.file:
        all_docs.extend(ingest_file(args.file, args.ocr))

    if args.dir:
        all_docs.extend(ingest_directory(args.dir, args.ocr))

    if args.url:
        print("\nDang doc website...")
        all_docs.extend(load_website(args.url, max_depth=args.depth, max_pages=20))

    if not all_docs:
        print("\nKhong co noi dung nao de nap!")
        sys.exit(0)

    print(f"\nTong tai lieu: {len(all_docs)} trang")

    # chunk
    chunks = split_documents(all_docs)
    clean_chunks = [c for c in chunks if c.page_content and c.page_content.strip()]

    if not clean_chunks:
        print("Khong co chunk hop le.")
        sys.exit(0)

    total = len(clean_chunks)

    print(f"\nBat dau ingest {total} chunks...")
    print(f"Batch size cấu hình: {BATCH_SIZE}")

    # ============================================================
    # INGEST WITH RATE LIMIT
    # ============================================================
    total_added = 0
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for b, i in enumerate(range(0, total, BATCH_SIZE), 1):
        batch = clean_chunks[i:i + BATCH_SIZE]

        print(f"\n-> Đang xử lý Batch {b}/{num_batches} ({len(batch)} chunks)")
        print(f"   Tiến độ: {min(i + BATCH_SIZE, total)}/{total}")

        attempt = 0
        while attempt < MAX_RETRY:
            try:
                added = vs.add_documents(batch)
                total_added += added
                break  # Thành công thì bẻ gãy vòng lặp retry, chuyển sang batch kế tiếp
            except Exception as e:
                if "429" in str(e):
                    backoff_sleep(attempt)
                    attempt += 1
                else:
                    raise  # Gặp lỗi hệ thống khác thì dừng để kiểm tra

        else:
            # Vòng lặp while kết thúc bình thường mà không dính lệnh break (quá số lần retry)
            print(f"\n[CRITICAL ERROR] Quá trình nạp bị gián đoạn: Thử lại {MAX_RETRY} lần đều thất bại do giới hạn API.")
            print("-> Hãy chạy lại lệnh cũ, hệ thống sẽ tự động resume từ chỗ dừng nhờ Checkpoint.")
            sys.exit(1)

        # Chủ động giãn cách an toàn giữa các batch thành công
        time.sleep(BASE_SLEEP)

    # =========================
    # DONE
    # =========================
    print(f"\n{'='*60}")
    print("HOAN THANH TIẾN TRÌNH NẠP")
    print(f"  Da nap moi: {total_added}")
    print(f"  Tong so record trong DB: {vs.count()}")

    sources = vs.get_sources()
    if sources:
        print(f"  Nguon tai lieu ({len(sources)}):")
        for s in sources:
            print(f"     - {s}")

    print(f"{'='*60}")
    print("\nChay chatbot: streamlit run app.py")


if __name__ == "__main__":
    main()