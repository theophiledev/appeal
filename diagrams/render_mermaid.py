"""
Render Mermaid diagrams from ALL_DIAGRAMS.md to PNG images
using the mermaid.ink API (no local dependencies needed).
"""
import re, base64, zlib, os, sys
import requests

MD_PATH = os.path.join(os.path.dirname(__file__), "ALL_DIAGRAMS.md")
OUT_DIR = os.path.join(os.path.dirname(__file__), "rendered")
os.makedirs(OUT_DIR, exist_ok=True)

with open(MD_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract all mermaid code blocks
pattern = re.compile(r'```mermaid\n(.*?)```', re.DOTALL)
blocks = pattern.findall(content)

print(f"Found {len(blocks)} mermaid diagram(s) in ALL_DIAGRAMS.md\n")

# Headers extracted from markdown structure to use as filenames
headers = re.findall(r'^## (\d+)\.\s+(.+)$', content, re.MULTILINE)

for idx, mermaid_code in enumerate(blocks):
    mermaid_code = mermaid_code.strip()

    # Determine diagram name
    if idx < len(headers):
        title = f"{headers[idx][0]}_{headers[idx][1].strip()}"
    else:
        title = f"diagram_{idx+1}"
    # Sanitize filename
    safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:60]
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')

    # Encode for mermaid.ink (deflate + base64)
    compressed = zlib.compress(mermaid_code.encode('utf-8'))
    encoded = base64.urlsafe_b64encode(compressed).decode('ascii')

    url = f"https://mermaid.ink/img/{encoded}"

    print(f"[{idx+1}/{len(blocks)}] Rendering: {safe_name}")

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            ext = "png"
            fpath = os.path.join(OUT_DIR, f"{safe_name}.{ext}")
            with open(fpath, 'wb') as f:
                f.write(resp.content)
            print(f"  -> Saved: {fpath} ({len(resp.content)} bytes)")
        else:
            print(f"  -> FAILED (HTTP {resp.status_code})")
            # Try SVG fallback
            url_svg = f"https://mermaid.ink/svg/{encoded}"
            resp2 = requests.get(url_svg, timeout=30)
            if resp2.status_code == 200:
                fpath = os.path.join(OUT_DIR, f"{safe_name}.svg")
                with open(fpath, 'wb') as f:
                    f.write(resp2.content)
                print(f"  -> Saved SVG fallback: {fpath}")
    except Exception as e:
        print(f"  -> ERROR: {e}")

print(f"\nDone. Check: {OUT_DIR}")
