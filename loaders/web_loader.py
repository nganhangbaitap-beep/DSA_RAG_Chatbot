# -*- coding: utf-8 -*-
# loaders/web_loader.py
# Đọc nội dung từ website cho RAG DSA Chatbot

import re
import time
import random
from urllib.parse import urljoin, urlparse
from langchain_core.documents import Document


def load_website(url: str, max_depth: int = 1, max_pages: int = 10) -> list[Document]:
    """
    Đọc nội dung từ website.
    Hỗ trợ crawl đệ quy (theo link nội bộ).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ Thiếu beautifulsoup4. Chạy: pip install beautifulsoup4 lxml")
        return []
    
    docs = []
    visited = set()
    
    # ─── TỐI ƯU 1: Dùng Session để giữ kết nối bền vững, tăng tốc và tránh bị chặn ───
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.google.com/"
    })
    
    print(f"🌐 Đang đọc website: {url}")
    print(f"   Độ sâu: {max_depth}, Tối đa: {max_pages} trang")
    
    def crawl(current_url: str, depth: int):
        if len(docs) >= max_pages or current_url in visited:
            return
        visited.add(current_url)
        
        # Chỉ delay kể từ trang thứ 2 trở đi để không lãng phí thời gian ở trang gốc
        if len(visited) > 1:
            time.sleep(random.uniform(1.0, 2.5))
            
        try:
            # Gọi request qua Session thay vì tạo mới liên tục
            response = session.get(current_url, timeout=15)
            
            # Xử lý lỗi HTTP tường minh thay vì crash im lặng bằng raise_for_status()
            if response.status_code == 403:
                print(f"   ⛔ 403 Forbidden (Bị chặn bot): {current_url}")
                return
            if response.status_code == 404:
                print(f"   ⚠️ 404 Not Found: {current_url}")
                return
            if response.status_code >= 400:
                print(f"   ⚠️ Lỗi HTTP {response.status_code}: {current_url}")
                return

            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "lxml")
            
            # Gỡ bỏ các thẻ rác làm nhiễu dữ liệu
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()
            
            # Tiêu đề trang
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)
            
            # Phân vùng nội dung chính
            main_content = (
                soup.find("main") or
                soup.find("article") or
                soup.find(id=re.compile(r"content|main|post", re.I)) or
                soup.find(class_=re.compile(r"content|main|article|post-body", re.I)) or
                soup.find("body")
            )
            
            if not main_content:
                return
            
            content_parts = []
            
            # ─── TỐI ƯU 2: Loại bỏ thẻ inline "code" để tránh bị lặp chữ với thẻ "p" bao ngoài ───
            for element in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "blockquote"]):
                text = element.get_text(separator=" ", strip=True)
                if not text or len(text) < 12:
                    continue
                
                tag = element.name
                if tag in ["h1", "h2", "h3", "h4"]:
                    content_parts.append(f"\n## {text}\n")
                elif tag == "pre":
                    content_parts.append(f"\n```\n{text}\n```\n")
                elif tag == "li":
                    content_parts.append(f"• {text}")
                elif tag == "blockquote":
                    content_parts.append(f"> {text}")
                else:
                    content_parts.append(text)
            
            full_text = "\n".join(content_parts)
            full_text = clean_web_text(full_text)
            
            if full_text and len(full_text) > 100:
                doc = Document(
                    page_content=full_text,
                    metadata={
                        "source": current_url,
                        "source_type": "website",
                        "title": title,
                        "domain": urlparse(current_url).netloc,
                        "depth": depth,
                    }
                )
                docs.append(doc)
                print(f"   ✅ Đọc thành công: {title[:40]}... ({len(full_text):,} ký tự)")
            
            # ─── FIX LỖI CRITICAL: Tiến hành thu thập và lọc link sạch TRƯỚC khi giới hạn lát cắt ───
            if depth < max_depth and len(docs) < max_pages:
                base_domain = urlparse(url).netloc
                valid_links = []
                
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "").strip()
                    
                    if not href or "undefined" in href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                        continue
                        
                    full_url = urljoin(current_url, href)
                    
                    if "undefined" in full_url:
                        continue
                    
                    # Chỉ lấy liên kết nội bộ và loại trừ các định dạng tệp tải về
                    if urlparse(full_url).netloc == base_domain:
                        if not re.search(r'\.(jpg|jpeg|png|gif|svg|ico|pdf|zip|tar|gz|exe)$', full_url, re.I):
                            if full_url not in visited:
                                valid_links.append(full_url)
                
                # Sau khi đã lọc sạch, lúc này mới lấy tối đa 20 link chất lượng nhất để tiếp tục crawl sâu hơn
                for next_url in valid_links[:20]:
                    if len(docs) >= max_pages:
                        break
                    crawl(next_url, depth + 1)
                    
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout khi kết nối: {current_url}")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Lỗi kết nối mạng: {current_url}")
        except Exception as e:
            print(f"   ⚠️ Lỗi không xác định tại {current_url}: {e}")
    
    crawl(url, 0)
    print(f"   📊 Tổng cộng: {len(docs)} trang đã nạp thành công.")
    return docs


def clean_web_text(text: str) -> str:
    """Làm sạch khoảng trắng thừa và định dạng văn bản."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()