#!/usr/bin/env python3
"""Translate HTML articles from English to Chinese using LibreTranslate API."""

import urllib.request
import urllib.parse
import json
import os
import re
import time
import html

SRC_DIR = "/root/.openclaw/workspace/site/articles"
DST_DIR = "/root/.openclaw/workspace/site/articles/zh"

FILES = [
    ("01-three-waves-of-ai.html", "AI的三次浪潮：从规则到大模型"),
    ("02-beyond-large-models.html", "超越大模型：AI的下一次范式转移"),
    ("03-ai-agents-from-tools-to-partners.html", "AI智能体：从工具到伙伴的进化"),
    ("04-open-vs-closed-source-ai.html", "开源与闭源AI：谁将胜出？"),
    ("05-ai-hardware-on-device-intelligence.html", "AI遇上硬件：端侧智能的崛起"),
]

# LibreTranslate public instances (try in order)
API_URLS = [
    "https://libretranslate.com/translate",
    "https://translate.terraprint.co/translate",
    "https://lt.vern.cc/translate",
]

def translate_text(text, src="en", tgt="zh", retries=3):
    """Translate text using LibreTranslate API."""
    if not text.strip():
        return text
    
    data = urllib.parse.urlencode({
        "q": text,
        "source": src,
        "target": tgt,
        "format": "text"
    }).encode("utf-8")
    
    for api_url in API_URLS:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(
                    api_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    translated = result.get("translatedText", text)
                    # Unescape HTML entities
                    translated = html.unescape(translated)
                    return translated
            except Exception as e:
                print(f"  Attempt {attempt+1} failed ({api_url}): {e}")
                time.sleep(2)
    
    # All APIs failed, return original
    print(f"  WARNING: All translation APIs failed for text snippet: {text[:60]}...")
    return text

def translate_in_chunks(text, max_chars=4500):
    """Translate long text by splitting into chunks at paragraph boundaries."""
    if len(text) <= max_chars:
        return translate_text(text)
    
    # Split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")
    translated_parts = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            translated_parts.append(translate_text(current_chunk.strip()))
            time.sleep(0.5)  # Rate limit
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
    
    if current_chunk.strip():
        translated_parts.append(translate_text(current_chunk.strip()))
    
    return "\n\n".join(translated_parts)

def extract_text_segments(html_content):
    """Extract translatable text segments from HTML, preserving structure."""
    # We'll work with the content between <article> tags
    # Strategy: find text content within HTML tags and translate them
    
    segments = []
    
    # Match text content inside tags (not inside attributes)
    # This regex finds text between > and < that isn't just whitespace
    pattern = re.compile(r'>([^<]+)<')
    
    for match in pattern.finditer(html_content):
        text = match.group(1).strip()
        if text and not text.startswith('{') and len(text) > 2:
            # Skip pure numbers, single chars, CSS-like content
            if not re.match(r'^[\d\s\.\,\-\:\;\%\+\/\(\)]+$', text):
                segments.append((match.start(), match.end(), text))
    
    return segments

def translate_html_file(src_path, dst_path, title_zh):
    """Translate an HTML file from English to Chinese."""
    print(f"\nProcessing: {os.path.basename(src_path)}")
    
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Structural changes
    content = content.replace('lang="en"', 'lang="zh"')
    
    # 2. Update canonical URL - add /zh/ before the filename
    content = re.sub(
        r'href="https://jianan-peng\.github\.io/articles/([^"]+)"',
        r'href="https://jianan-peng.github.io/articles/zh/\1"',
        content
    )
    
    # 3. Update nav links: href="../" -> href="../../"
    content = content.replace('href="../"', 'href="../../"')
    
    # 4. Update title
    old_title = re.search(r'<title>([^<]+)</title>', content)
    if old_title:
        # Extract the "– AI Insights" suffix
        suffix_match = re.search(r'\s*[–-]\s*AI Insights', old_title.group(1))
        suffix = " – AI 洞察" if suffix_match else ""
        content = content.replace(old_title.group(0), f'<title>{title_zh}{suffix}</title>')
    
    # 5. Update meta description - translate it
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    if desc_match:
        desc_en = desc_match.group(1)
        print(f"  Translating meta description...")
        desc_zh = translate_text(desc_en)
        content = content.replace(desc_match.group(0), 
                                   f'<meta name="description" content="{desc_zh}"')
    
    # 6. Translate article content
    # Extract article section
    article_match = re.search(r'(<article>)(.*?)(</article>)', content, re.DOTALL)
    if not article_match:
        print(f"  ERROR: No <article> tag found!")
        return
    
    article_content = article_match.group(2)
    
    # Find all text segments in the article
    segments = []
    pattern = re.compile(r'>([^<]+)<')
    for match in pattern.finditer(article_content):
        text = match.group(1).strip()
        if text and len(text) > 2 and not text.startswith('{'):
            if not re.match(r'^[\d\s\.\,\-\:\;\%\+\/\(\)~]+$', text):
                segments.append((match.start(1), match.end(1), text))
    
    print(f"  Found {len(segments)} text segments to translate")
    
    # Translate segments in batches
    translated_segments = []
    batch_texts = []
    batch_indices = []
    
    BATCH_SIZE = 5  # Translate 5 segments at a time
    MAX_CHARS = 4000
    
    for i, (start, end, text) in enumerate(segments):
        batch_texts.append(text)
        batch_indices.append(i)
        
        current_chars = sum(len(t) for t in batch_texts)
        
        if len(batch_texts) >= BATCH_SIZE or current_chars > MAX_CHARS or i == len(segments) - 1:
            # Translate this batch
            combined = "\n|||\n".join(batch_texts)
            print(f"  Translating batch {len(translated_segments)//BATCH_SIZE + 1} ({len(batch_texts)} segments, {len(combined)} chars)...")
            
            translated_combined = translate_in_chunks(combined)
            translated_parts = translated_combined.split("\n|||\n")
            
            # Handle mismatch
            if len(translated_parts) != len(batch_texts):
                print(f"  WARNING: Segment count mismatch ({len(translated_parts)} vs {len(batch_texts)}), using individual translation")
                for j, text in enumerate(batch_texts):
                    translated_segments.append(translate_text(text))
                    time.sleep(0.3)
            else:
                translated_segments.extend(translated_parts)
            
            batch_texts = []
            batch_indices = []
            time.sleep(1)  # Rate limit between batches
    
    # Reconstruct article content with translations
    # We need to replace text segments in reverse order to preserve positions
    result = article_content
    for i in range(len(segments) - 1, -1, -1):
        start, end, text = segments[i]
        if i < len(translated_segments):
            translated = translated_segments[i]
            # Replace the text within the tag
            result = result[:start] + translated + result[end:]
    
    # Reconstruct full HTML
    full_html = content[:article_match.start(2)] + result + content[article_match.end(2):]
    
    # Write output
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"  ✓ Saved to {dst_path}")

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    
    for filename, title_zh in FILES:
        src_path = os.path.join(SRC_DIR, filename)
        dst_path = os.path.join(DST_DIR, filename)
        
        if not os.path.exists(src_path):
            print(f"ERROR: Source file not found: {src_path}")
            continue
        
        translate_html_file(src_path, dst_path, title_zh)
    
    print("\n" + "="*60)
    print("All files processed!")
    print("="*60)

if __name__ == "__main__":
    main()
