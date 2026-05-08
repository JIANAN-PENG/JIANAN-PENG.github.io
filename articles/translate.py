#!/usr/bin/env python3
"""Translate HTML articles from English to Chinese using Google Translate API."""

import urllib.request
import urllib.parse
import json
import os
import re
import time
import html as html_module
from html.parser import HTMLParser

SRC_DIR = "/root/.openclaw/workspace/site/articles"
DST_DIR = "/root/.openclaw/workspace/site/articles/zh"

FILES = [
    ("01-three-waves-of-ai.html", "AI的三次浪潮：从规则到大模型"),
    ("02-beyond-large-models.html", "超越大模型：AI的下一次范式转移"),
    ("03-ai-agents-from-tools-to-partners.html", "AI智能体：从工具到伙伴的进化"),
    ("04-open-vs-closed-source-ai.html", "开源与闭源AI：谁将胜出？"),
    ("05-ai-hardware-on-device-intelligence.html", "AI遇上硬件：端侧智能的崛起"),
]

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
CHUNK_SIZE = 3000  # chars per request
SEPARATOR = "\n||||\n"  # separator for batching

def google_translate(text, src="en", tgt="zh-CN"):
    """Translate text using Google Translate unofficial API."""
    if not text.strip():
        return text
    
    params = urllib.parse.urlencode({
        "client": "gtx",
        "sl": src,
        "tl": tgt,
        "dt": "t",
        "q": text
    })
    url = f"{GOOGLE_TRANSLATE_URL}?{params}"
    
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        translated = "".join([s[0] for s in result[0] if s[0]])
        return translated

def translate_segments(segments):
    """Translate a list of text segments, batching them efficiently."""
    if not segments:
        return []
    
    results = [""] * len(segments)
    batch = []
    batch_indices = []
    batch_chars = 0
    
    for i, text in enumerate(segments):
        text_stripped = text.strip()
        if not text_stripped or len(text_stripped) <= 1:
            results[i] = text
            continue
        
        batch.append(text_stripped)
        batch_indices.append(i)
        batch_chars += len(text_stripped)
        
        if batch_chars >= CHUNK_SIZE or len(batch) >= 20 or i == len(segments) - 1:
            # Translate batch
            combined = SEPARATOR.join(batch)
            try:
                translated = google_translate(combined)
                parts = translated.split("||||")
                
                # Clean up parts
                parts = [p.strip() for p in parts]
                
                if len(parts) == len(batch):
                    for j, idx in enumerate(batch_indices):
                        results[idx] = parts[j]
                else:
                    # Mismatch - translate individually
                    print(f"  Batch mismatch ({len(parts)} vs {len(batch)}), translating individually...")
                    for j, idx in enumerate(batch_indices):
                        try:
                            results[idx] = google_translate(batch[j])
                            time.sleep(0.2)
                        except:
                            results[idx] = batch[j]
                
            except Exception as e:
                print(f"  Translation error: {e}")
                # Fallback: translate individually
                for j, idx in enumerate(batch_indices):
                    try:
                        results[idx] = google_translate(batch[j])
                        time.sleep(0.3)
                    except:
                        results[idx] = batch[j]
            
            batch = []
            batch_indices = []
            batch_chars = 0
            time.sleep(0.5)  # Rate limit
    
    return results

class TextExtractor(HTMLParser):
    """Extract text content from HTML, tracking positions."""
    
    def __init__(self):
        super().__init__()
        self.segments = []  # (start_pos, end_pos, text, tag_context)
        self.skip_tags = {'script', 'style', 'code', 'pre'}
        self.current_tag_stack = []
        self.in_skip = False
    
    def handle_starttag(self, tag, attrs):
        self.current_tag_stack.append(tag)
        if tag in self.skip_tags:
            self.in_skip = True
    
    def handle_endtag(self, tag):
        if self.current_tag_stack and self.current_tag_stack[-1] == tag:
            self.current_tag_stack.pop()
        if tag in self.skip_tags:
            self.in_skip = False
    
    def handle_data(self, data):
        if self.in_skip:
            return
        text = data.strip()
        if text and len(text) > 1:
            self.segments.append(text)

def extract_article_content(html_content):
    """Extract the article body content."""
    match = re.search(r'(<article[^>]*>)(.*?)(</article>)', html_content, re.DOTALL)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None, html_content, None

def translate_article_body(article_html):
    """Translate all text content within the article body."""
    # Find all text segments between HTML tags
    # Pattern: text between > and < that contains actual content
    pattern = re.compile(r'>([^<]+)<')
    
    segments = []
    positions = []
    
    for match in pattern.finditer(article_html):
        text = match.group(1)
        text_stripped = text.strip()
        
        # Skip empty, very short, or non-translatable content
        if not text_stripped or len(text_stripped) <= 1:
            continue
        if text_stripped.startswith('{') or text_stripped.startswith('//'):
            continue
        # Skip pure numbers/dates/symbols
        if re.match(r'^[\d\s\.\,\-\:\;\%\+\/\(\)~–—]+$', text_stripped):
            continue
        
        segments.append(text_stripped)
        positions.append((match.start(1), match.end(1)))
    
    print(f"  Extracted {len(segments)} text segments")
    
    # Translate all segments
    print(f"  Translating...")
    translated = translate_segments(segments)
    
    # Reconstruct article HTML with translated text (reverse order to preserve positions)
    result = article_html
    for i in range(len(positions) - 1, -1, -1):
        start, end = positions[i]
        if translated[i]:
            # Preserve leading/trailing whitespace from original
            original = article_html[start:end]
            leading = len(original) - len(original.lstrip())
            trailing = len(original) - len(original.rstrip())
            
            new_text = translated[i]
            if leading:
                new_text = original[:leading] + new_text
            if trailing:
                new_text = new_text + original[-trailing:]
            
            result = result[:start] + new_text + result[end:]
    
    return result

def translate_html_file(src_path, dst_path, title_zh):
    """Translate an HTML file from English to Chinese."""
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(src_path)}")
    print(f"{'='*60}")
    
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # === Structural changes ===
    
    # 1. Language attribute
    content = content.replace('lang="en"', 'lang="zh"')
    
    # 2. Canonical URL - add /zh/
    content = re.sub(
        r'href="https://jianan-peng\.github\.io/articles/([^"]+)"',
        r'href="https://jianan-peng.github.io/articles/zh/\1"',
        content
    )
    
    # 3. Nav links: ../ -> ../../
    content = content.replace('href="../"', 'href="../../"')
    
    # 4. Title
    title_match = re.search(r'<title>([^<]+)</title>', content)
    if title_match:
        content = content.replace(
            title_match.group(0),
            f'<title>{title_zh} – AI 洞察</title>'
        )
    print(f"  Title: {title_zh}")
    
    # 5. Meta description
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    if desc_match:
        desc_en = desc_match.group(1)
        print(f"  Translating meta description...")
        try:
            desc_zh = google_translate(desc_en)
            content = content.replace(
                f'content="{desc_en}"',
                f'content="{desc_zh}"',
                1
            )
        except Exception as e:
            print(f"  Failed to translate description: {e}")
        time.sleep(0.5)
    
    # 6. Translate article body
    article_match = re.search(r'(<article[^>]*>)(.*?)(</article>)', content, re.DOTALL)
    if article_match:
        article_body = article_match.group(2)
        print(f"  Article body: {len(article_body)} chars")
        
        translated_body = translate_article_body(article_body)
        
        content = (
            content[:article_match.start(2)] +
            translated_body +
            content[article_match.end(2):]
        )
    else:
        print(f"  WARNING: No <article> tag found!")
    
    # Write output
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\n  ✓ Saved: {dst_path}")

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    
    for filename, title_zh in FILES:
        src_path = os.path.join(SRC_DIR, filename)
        dst_path = os.path.join(DST_DIR, filename)
        
        if not os.path.exists(src_path):
            print(f"ERROR: Source file not found: {src_path}")
            continue
        
        translate_html_file(src_path, dst_path, title_zh)
    
    print(f"\n{'='*60}")
    print("All files processed!")
    print(f"{'='*60}")
    
    # List output files
    print(f"\nGenerated files in {DST_DIR}:")
    for f in sorted(os.listdir(DST_DIR)):
        if f.endswith('.html'):
            size = os.path.getsize(os.path.join(DST_DIR, f))
            print(f"  {f} ({size:,} bytes)")

if __name__ == "__main__":
    main()
