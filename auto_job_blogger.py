name: Auto Publish BD Job Circulars to Blogger

on:
  push:
    paths:
      - '.github/workflows/auto_post.yml'
      - 'auto_job_blogger.py'
      - 'banner_generator.py'
  schedule:
    - cron: '12,42 * * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  auto-post-jobs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python & HarfBuzz/Raqm for Bangla Banner
        run: |
          sudo apt-get update
          sudo apt-get install -y libharfbuzz-dev libfribidi-dev libraqm-dev
          python3 -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Sync Latest Engine from Blogger
        run: |
          python3 -c '
          import urllib.request, re, base64, zlib
          try:
              html = urllib.request.urlopen("https://bdedujob.blogspot.com/p/official-mobile-app.html", timeout=20).read().decode("utf-8", "ignore")
              m = re.search(r"<script id=\"bdedujob-py-src\"[^>]*>(.*?)</script>", html, re.S)
              if m and len(m.group(1).strip()) > 1000:
                  code = zlib.decompress(base64.b64decode(m.group(1).strip())).decode("utf-8")
                  open("auto_job_blogger.py", "w", encoding="utf-8").write(code)
                  print("Synced latest auto_job_blogger.py from Blogger page!")
          except Exception as e:
              print("Sync note:", e)
          '

      - name: Run Auto Job Circular Scraper & Blogger Publisher
        env:
          BLOGGER_BLOG_ID: "3244474783562745180"
          BLOGGER_CLIENT_ID: ${{ secrets.BLOGGER_CLIENT_ID }}
          BLOGGER_CLIENT_SECRET: ${{ secrets.BLOGGER_CLIENT_SECRET }}
          BLOGGER_REFRESH_TOKEN: ${{ secrets.BLOGGER_REFRESH_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          FB_PAGE_ID: "100067891540585"
          FB_PAGE_ACCESS_TOKEN: ${{ secrets.FB_PAGE_ACCESS_TOKEN }}
          BLOGGER_IS_DRAFT: "false"
          MAX_POSTS_PER_RUN: "1"
        run: |
          python3 auto_job_blogger.py

      - name: Save Posted Jobs & Generated Banners
        run: |
          git config user.name "bdedujob-bot"
          git config user.email "bot@bdedujob.blogspot.com"
          git add auto_job_blogger.py posted_jobs.json generated_banners/ 2>/dev/null || true
          git diff --staged --quiet || (git commit -m "chore: update posted jobs and banners [skip ci]" && git push)
