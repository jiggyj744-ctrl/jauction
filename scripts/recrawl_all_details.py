"""
전체 상세 재크롤링 스크립트
- detail_scraped를 0으로 리셋
- crawler.py의 crawl_details_parallel()로 33,448건 전체 재크롤링
- 신규 필드: appraisal_report, status_report, building_structure, claim_deadline,
  appraisal_summary, auction_tenants, auction_documents 등
"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import sqlite3
from datetime import datetime

DB_PATH = 'data/auction.db'

# Step 1: Reset detail_scraped for ALL items
print("=" * 60)
print("전체 상세 재크롤링 시작")
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM auction_items')
total = cursor.fetchone()[0]
print(f"\n총 물건: {total}건")

cursor.execute('UPDATE auction_items SET detail_scraped = 0')
conn.commit()
print(f"detail_scraped 전체 리셋 완료 ({total}건 → 0)")

conn.close()

# Step 2: Run detail crawling
print(f"\n상세 크롤링 시작 (20병렬)...")
print(f"예상 소요: 3~4시간\n")

from crawler import crawl_details_parallel
crawl_details_parallel(num_workers=20)

# Step 3: Show results
print("\n" + "=" * 60)
print("재크롤링 완료!")
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report IS NOT NULL AND appraisal_report != ''")
print(f"appraisal_report: {cursor.fetchone()[0]}건")

cursor.execute("SELECT COUNT(*) FROM auction_items WHERE status_report IS NOT NULL AND status_report != ''")
print(f"status_report: {cursor.fetchone()[0]}건")

cursor.execute("SELECT COUNT(*) FROM auction_items WHERE building_structure IS NOT NULL AND building_structure != ''")
print(f"building_structure: {cursor.fetchone()[0]}건")

cursor.execute("SELECT COUNT(*) FROM auction_items WHERE claim_deadline IS NOT NULL AND claim_deadline != ''")
print(f"claim_deadline: {cursor.fetchone()[0]}건")

cursor.execute('SELECT COUNT(*) FROM auction_tenants')
print(f"auction_tenants: {cursor.fetchone()[0]}건")

cursor.execute('SELECT COUNT(*) FROM auction_documents')
print(f"auction_documents: {cursor.fetchone()[0]}건")

conn.close()