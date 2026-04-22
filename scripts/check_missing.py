import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM auction_items')
total = c.fetchone()[0]
print(f'총 물건: {total:,}')

c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1')
detail_done = c.fetchone()[0]
print(f'상세 수집 완료: {detail_done:,} ({detail_done/total*100:.1f}%)')
print(f'상세 미수집: {total - detail_done:,} ({(total-detail_done)/total*100:.1f}%)')

print('\n--- 컬럼별 충족률 ---')
for col in ['risk_keywords', 'risk_score', 'lat', 'lon', 'building_structure', 
            'building_roof', 'total_floors', 'target_floor', 'heating_type', 'parking_available', 
            'elevator_available', 'land_use_plan', 'appraisal_summary', 'appraisal_report', 
            'status_report', 'claim_deadline', 'sale_rate', 'address_sigungu', 'difficulty_grade']:
    try:
        c.execute(f"SELECT COUNT(*) FROM auction_items WHERE [{col}] IS NOT NULL AND [{col}] != '' AND [{col}] != 0")
        filled = c.fetchone()[0]
        status = '✅' if filled > 0 else '❌'
        print(f'  {status} {col}: {filled:,}/{total:,} ({filled/total*100:.1f}%)')
    except Exception as e:
        print(f'  ❓ {col}: 컬럼 없음 ({e})')

print('\n--- 보조 테이블 ---')
for tbl in ['auction_bid_history', 'auction_images', 'auction_registry', 'auction_tenants', 'auction_documents', 'item_changes']:
    try:
        c.execute(f'SELECT COUNT(*) FROM {tbl}')
        cnt = c.fetchone()[0]
        print(f'  {tbl}: {cnt:,}건')
    except:
        print(f'  {tbl}: 테이블 없음')

print('\n--- 스크립트 파일 존재 여부 ---')
import os
scripts = {
    'risk_tagger.py': '리스크 태깅',
    'geocode_batch.py': '위경도 변환',
    'expert_comment.py': 'AI 전문가 코멘트',
    'download_pdfs.py': 'PDF 다운로드',
    'fix_all.py': '원스톱 데이터 보완',
    'generate_site.py': '정적 사이트 생성',
}
for f, desc in scripts.items():
    exists = os.path.exists(f)
    print(f'  {"✅" if exists else "❌"} {f}: {desc}')

conn.close()