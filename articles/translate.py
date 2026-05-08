#!/usr/bin/env python3
"""Translate HTML articles from English to Chinese using Google Translate API."""

import urllib.request
import urllib.parse
import json
import os
import re
import time

SRC_DIR = "/root/.openclaw/workspace/site/articles"
DST_DIR = "/root/.openclaw/workspace/site/articles/zh"

FILES = [
    ("01-three-waves-of-ai.html", "AI的三次浪潮：从规则到大模型"),
    ("02-beyond-large-models.html", "超越大模型：AI的下一次范式转移"),
    ("03-ai-agents-from-tools-to-partners.html", "AI智能体：从工具到伙伴的进化"),
    ("04-open-vs-closed-source-ai.html", "开源与闭源AI：谁将胜出？"),
    ("05-ai-hardware-on-device-intelligence.html", "AI遇上硬件：端侧智能的崛起"),
]

CHUNK_SIZE = 3000
SEPARATOR = "\n||||\n"

def google_translate(text, retries=3):
    if not text.strip():
        return text
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text
    })
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return "".join([s[0] for s in result[0] if s[0]])
        except Exception as e:
            print(f"    Retry {attempt+1}: {e}")
            time.sleep(2)
    return text

def translate_segments(segments):
    if not segments:
        return []
    results = [""] * len(segments)
    batch_texts = []
    batch_indices = []
    batch_chars = 0

    for i, text in enumerate(segments):
        ts = text.strip()
        if not ts or len(ts) <= 1:
            results[i] = text
            continue
        batch_texts.append(ts)
        batch_indices.append(i)
        batch_chars += len(ts)

        if batch_chars >= CHUNK_SIZE or len(batch_texts) >= 15 or i == len(segments) - 1:
            combined = SEPARATOR.join(batch_texts)
            try:
                translated = google_translate(combined)
                parts = [p.strip() for p in translated.split("||||")]
                if len(parts) == len(batch_texts):
                    for j, idx in enumerate(batch_indices):
                        results[idx] = parts[j]
                else:
                    print(f"    Mismatch ({len(parts)} vs {len(batch_texts)}), individual...")
                    for j, idx in enumerate(batch_indices):
                        results[idx] = google_translate(batch_texts[j])
                        time.sleep(0.3)
            except Exception as e:
                print(f"    Batch error: {e}")
                for j, idx in enumerate(batch_indices):
                    try:
                        results[idx] = google_translate(batch_texts[j])
                        time.sleep(0.3)
                    except:
                        results[idx] = batch_texts[j]
            batch_texts = []
            batch_indices = []
            batch_chars = 0
            time.sleep(0.5)
    return results

def translate_html_file(src_path, dst_path, title_zh):
    print(f"\n{'='*60}\nProcessing: {os.path.basename(src_path)}\n{'='*60}")
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Structural changes
    content = content.replace('lang="en"', 'lang="zh"')
    content = re.sub(
        r'href="https://jianan-peng\.github\.io/articles/([^"]+)"',
        r'href="https://jianan-peng.github.io/articles/zh/\1"', content)
    content = content.replace('href="../"', 'href="../../"')

    # Title
    title_match = re.search(r'<title>([^<]+)</title>', content)
    if title_match:
        content = content.replace(title_match.group(0), f'<title>{title_zh} – AI 洞察</title>')
    print(f"  Title: {title_zh}")

    # Meta description
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
    if desc_match:
        desc_en = desc_match.group(1)
        print(f"  Translating description...")
        desc_zh = google_translate(desc_en)
        content = content.replace(f'content="{desc_en}"', f'content="{desc_zh}"', 1)
        time.sleep(0.5)

    # Extract article body
    article_match = re.search(r'(<article[^>]*>)(.*?)(</article>)', content, re.DOTALL)
    if not article_match:
        print("  ERROR: No <article> tag!")
        return

    article_body = article_match.group(2)
    print(f"  Article body: {len(article_body)} chars")

    # Find text segments
    pattern = re.compile(r'>([^<]+)<')
    segments = []
    positions = []
    for match in pattern.finditer(article_body):
        text = match.group(1)
        ts = text.strip()
        if not ts or len(ts) <= 1:
            continue
        if ts.startswith('{') or ts.startswith('//'):
            continue
        if re.match(r'^[\d\s\.\,\-\:\;\%\+\/\(\)~–—]+$', ts):
            continue
        segments.append(ts)
        positions.append((match.start(1), match.end(1)))

    print(f"  Found {len(segments)} text segments")

    # Translate
    print(f"  Translating...")
    translated = translate_segments(segments)

    # Reconstruct (reverse order)
    result = article_body
    for i in range(len(positions) - 1, -1, -1):
        start, end = positions[i]
        if translated[i]:
            orig = article_body[start:end]
            leading = len(orig) - len(orig.lstrip())
            trailing = len(orig) - len(orig.rstrip())
            new_text = translated[i]
            if leading:
                new_text = orig[:leading] + new_text
            if trailing:
                new_text = new_text + orig[-trailing:]
            result = result[:start] + new_text + result[end:]

    content = content[:article_match.start(2)] + result + content[article_match.end(2):]

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Saved: {dst_path}")

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    for filename, title_zh in FILES:
        src_path = os.path.join(SRC_DIR, filename)
        dst_path = os.path.join(DST_DIR, filename)
        if not os.path.exists(src_path):
            print(f"ERROR: {src_path} not found")
            continue
        translate_html_file(src_path, dst_path, title_zh)

    print(f"\n{'='*60}\nAll done!\n{'='*60}")
    print(f"\nFiles in {DST_DIR}:")
    for f in sorted(os.listdir(DST_DIR)):
        if f.endswith('.html'):
            size = os.path.getsize(os.path.join(DST_DIR, f))
            print(f"  {f} ({size:,} bytes)")

if __name__ == "__main__":
    main()
