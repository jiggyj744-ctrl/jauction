"""전체 크롤링 결과 분석 - 미비건, 실패건, PDF 현황 종합"""
import sqlite3
import json

conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

print("=" * 70)
print("전체 크롤링 결과 분석")
print("=" * 70)

# 1. 기본 현황
c.execute('SELECT COUNT(*) FROM auction_items')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1')
scraped = c.fetchone()[0]
not_scraped = total - scraped
print(f"\n[1] 기본 현황")
print(f"  전체: {total}, 스크랩완료: {scraped} ({scraped*100/total:.1f}%), 미처리: {not_scraped}")

# 2. 미처리 건 분석
print(f"\n[2] 미처리 건 ({not_scraped}건)")
c.execute("SELECT internal_id, case_number, status, item_type, court FROM auction_items WHERE detail_scraped = 0 OR detail_scraped IS NULL LIMIT 20")
rows = c.fetchall()
if rows:
    for r in rows:
        print(f"  ID:{r[0]} 사건:{r[1]} 상태:{r[2]} 종류:{r[3]} 법원:{r[4]}")
else:
    print("  없음 - 전체 완료!")

# 3. 필드별 미비 현황
print(f"\n[3] 필드별 미비 현황 (detail_scraped=1 중)")
fields = [
    ('appraisal_report', '감정평가서'),
    ('status_report', '현황조사서'),
    ('appraisal_summary', '감정평가요약'),
    ('claim_deadline', '배당요구종기'),
    ('building_structure', '건물구조'),
    ('notes', '참고사항'),
    ('address', '소재지'),
    ('creditor', '채권자'),
    ('debtor', '채무자'),
    ('owner', '소유자'),
    ('pdf_urls', 'PDF URL'),
    ('sale_statement', '매각물건명세서'),
    ('property_list', '부동산표시'),
    ('delivery_records', '송달내역'),
]
for field, name in fields:
    c.execute(f"SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1 AND ({field} IS NULL OR {field} = '')")
    missing = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1 AND {field} IS NOT NULL AND {field} != ''")
    filled = c.fetchone()[0]
    pct = filled * 100 / scraped if scraped > 0 else 0
    print(f"  {name:15s}: {filled:5d}건 채움 / {missing:5d}건 비어있음 ({pct:.1f}%)")

# 4. PDF 상세 현황
print(f"\n[4] PDF 파일 현황")
c.execute("SELECT COUNT(*) FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != ''")
pdf_filled = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1 AND (pdf_urls IS NULL OR pdf_urls = '')")
pdf_missing = c.fetchone()[0]
print(f"  PDF URL 있음: {pdf_filled}건")
print(f"  PDF URL 없음 (스크랩완료 중): {pdf_missing}건")

# 총 PDF 파일 수
c.execute("SELECT pdf_urls FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != ''")
total_pdfs = 0
for row in c.fetchall():
    try:
        urls = json.loads(row[0])
        total_pdfs += len(urls)
    except:
        pass
print(f"  총 PDF 파일 수: {total_pdfs}개")

# 5. 물건종류별 스크랩 현황
print(f"\n[5] 물건종류별 현황")
c.execute("""
    SELECT item_type, COUNT(*) as cnt,
           SUM(CASE WHEN detail_scraped=1 THEN 1 ELSE 0 END) as scraped
    FROM auction_items
    GROUP BY item_type
    ORDER BY cnt DESC
""")
for r in c.fetchall():
    pct = r[2]*100/r[1] if r[1] > 0 else 0
    missing = r[1] - r[2]
    print(f"  {str(r[0] or '미확인'):12s}: {r[1]:5d}건 중 {r[2]:5d} 완료 ({pct:.1f}%) 미처리:{missing}")

# 6. 상태별 현황
print(f"\n[6] 상태별 현황")
c.execute("""
    SELECT status, COUNT(*) as cnt,
           SUM(CASE WHEN detail_scraped=1 THEN 1 ELSE 0 END) as scraped
    FROM auction_items
    GROUP BY status
    ORDER BY cnt DESC
""")
for r in c.fetchall():
    pct = r[2]*100/r[1] if r[1] > 0 else 0
    missing = r[1] - r[2]
    print(f"  {str(r[0] or '미확인'):10s}: {r[1]:5d}건 중 {r[2]:5d} 완료 ({pct:.1f}%) 미처리:{missing}")

# 7. 카테고리별 임차인/문서 현황
print(f"\n[7] 관련 테이블 현황")
c.execute("SELECT COUNT(*) FROM auction_tenants")
tenants = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT internal_id) FROM auction_tenants")
tenant_items = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM auction_documents")
docs = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT internal_id) FROM auction_documents")
doc_items = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM auction_bid_history")
bids = c.fetchone()[0]
print(f"  임차인: {tenants}건 ({tenant_items}개 물건)")
print(f"  문건접수: {docs}건 ({doc_items}개 물건)")
print(f"  입찰이력: {bids}건")

# 8. 이미지 현황
print(f"\n[8] 이미지 현황")
c.execute("SELECT COUNT(*) FROM auction_images WHERE downloaded = 1")
img_dl = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM auction_images")
img_total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM auction_items WHERE photo_urls IS NOT NULL AND photo_urls != ''")
photo_filled = c.fetchone()[0]
print(f"  photo_urls 있음: {photo_filled}건")
print(f"  이미지 DB: {img_dl}/{img_total} 다운로드됨")

conn.close()

print("\n" + "=" * 70)
print("분석 완료")