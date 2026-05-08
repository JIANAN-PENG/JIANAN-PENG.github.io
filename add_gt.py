#!/usr/bin/env python3
"""Add Google Translate to all article HTML files."""
import os
import glob

ARTICLES_DIR = '/root/.openclaw/workspace/site/articles'

GT_SCRIPT = """
<!-- Google Translate -->
<div id="google_translate_element" style="display:none;"></div>
<style>.goog-te-banner-frame{display:none!important}body{top:0!important}.skiptranslate{display:none!important}</style>
<script type="text/javascript">
function googleTranslateElementInit(){
  new google.translate.TranslateElement({pageLanguage:'en',autoDisplay:false},'google_translate_element');
}
</script>
<script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
"""

def add_gt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'google_translate_element' in content:
        print(f"  Skip: {os.path.basename(filepath)}")
        return
    
    # Insert before </body>
    content = content.replace('</body>', GT_SCRIPT + '\n</body>', 1)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Updated: {os.path.basename(filepath)}")

def main():
    print("Adding Google Translate to article pages...")
    for f in sorted(glob.glob(os.path.join(ARTICLES_DIR, '*.html'))):
        add_gt(f)
    print("Done!")

if __name__ == '__main__':
    main()
