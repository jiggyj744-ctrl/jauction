import sqlite3
import json
import requests
import time
from collections import Counter

conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# 1. PDF URL 통계
c.execute("SELECT pdf_urls FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != ''")
rows = c.fetchall()

url_count = 0
domains = Counter()
path_patterns = Counter()
sample_urls = []

for row in rows:
    try:
        urls = json.loads(row[0])
        for u in urls:
            url_count += 1
            # 도메인 추출
            if 'file2.nuriauction.com' in u:
                domains['file2.nuriauction.com'] += 1
            elif 'file.nuriauction.com' in u:
                domains['file.nuriauction.com'] += 1
            elif 'gfauction.co.kr' in u:
                domains['gfauction.co.kr'] += 1
            else:
                # 다른 도메인
                parts = u.split('/')
                if len(parts) >= 3:
                    domains[parts[2]] += 1
                else:
                    domains['unknown'] += 1
            
            if len(sample_urls) < 5:
                sample_urls.append(u)
    except:
        pass

print(f"총 PDF 파일 수: {url_count}")
print(f"총 물건 수: {len(rows)}")
print(f"\n도메인 분포:")
for domain, cnt in domains.most_common():
    print(f"  {domain}: {cnt}")

# 2. PDF당 개수 분포
pdfs_per_item = []
for row in rows:
    try:
        urls = json.loads(row[0])
        pdfs_per_item.append(len(urls))
    except:
        pdfs_per_item.append(0)

pdf_count_dist = Counter(pdfs_per_item)
print(f"\n물건당 PDF 개수 분포:")
for cnt, freq in sorted(pdf_count_dist.items()):
    print(f"  {cnt}개 PDF: {freq}건")

# 3. 실제 다운로드 테스트 (1개만)
print(f"\n--- 다운로드 테스트 ---")
if sample_urls:
    test_url = sample_urls[0]
    print(f"URL: {test_url}")
    try:
        start = time.time()
        resp = requests.get(test_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        elapsed = time.time() - start
        print(f"HTTP Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"Content-Length: {len(resp.content)} bytes ({len(resp.content)/1024:.1f} KB)")
        print(f"응답 시간: {elapsed:.2f}초")
        print(f"로그인 필요 여부: {'아니요 (직접 접근 가능)' if resp.status_code == 200 and '%PDF' in resp.text[:10] else '확인 필요'}")
        if resp.status_code == 200 and len(resp.content) > 100:
            print(f"PDF 시그니처: {resp.content[:20]}")
    except Exception as e:
        print(f"에러: {e}")

conn.close()