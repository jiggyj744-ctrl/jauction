import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()
total = 33448

print('=== 현재 충족률이 낮은 컬럼 ===')
for col in ['building_roof', 'total_floors', 'target_floor', 'land_use_plan', 'parking_available', 'sale_rate', 'sale_statement', 'property_list', 'delivery_records', 'pdf_urls']:
    try:
        c.execute(f"SELECT COUNT(*) FROM auction_items WHERE [{col}] IS NOT NULL AND [{col}] != '' AND [{col}] != 0")
        filled = c.fetchone()[0]
        print(f'  {col}: {filled:,}/{total:,} ({filled/total*100:.1f}%)')
    except Exception as e:
        print(f'  {col}: 오류 ({e})')

print()
print('=== 샘플: status_report 앞부분 (3건) ===')
c.execute("SELECT internal_id, substr(status_report, 1, 500) FROM auction_items WHERE status_report IS NOT NULL AND status_report != '' LIMIT 3")
for row in c.fetchall():
    print(f'  [{row[0]}] {row[1][:400]}')
    print('  ---')

print()
print('=== 샘플: sale_statement 앞부분 (3건) ===')
c.execute("SELECT internal_id, substr(sale_statement, 1, 500) FROM auction_items WHERE sale_statement IS NOT NULL AND sale_statement != '' LIMIT 3")
for row in c.fetchall():
    print(f'  [{row[0]}] {row[1][:400]}')
    print('  ---')

print()
print('=== 샘플: property_list 앞부분 (3건) ===')
c.execute("SELECT internal_id, substr(property_list, 1, 500) FROM auction_items WHERE property_list IS NOT NULL AND property_list != '' LIMIT 3")
for row in c.fetchall():
    print(f'  [{row[0]}] {row[1][:400]}')
    print('  ---')

print()
print('=== 샘플: delivery_records 앞부분 (3건) ===')
c.execute("SELECT internal_id, substr(delivery_records, 1, 500) FROM auction_items WHERE delivery_records IS NOT NULL AND delivery_records != '' LIMIT 3")
for row in c.fetchall():
    print(f'  [{row[0]}] {row[1][:400]}')
    print('  ---')

print()
print('=== 샘플: notes 앞부분 (5건) ===')
c.execute("SELECT internal_id, substr(notes, 1, 300) FROM auction_items WHERE notes IS NOT NULL AND notes != '' LIMIT 5")
for row in c.fetchall():
    print(f'  [{row[0]}] {row[1][:250]}')
    print('  ---')

print()
print('=== 샘플: appraisal_report에서 추가 파싱 가능한 패턴 탐색 ===')
# 1. 점유자/현황 정보
c.execute("SELECT COUNT(*) FROM auction_items WHERE status_report LIKE '%점유%' OR status_report LIKE '%거주%' OR status_report LIKE '%임대%'")
print(f'  status_report에 점유/거주/임대 언급: {c.fetchone()[0]:,}건')

# 2. 법원/담당부서 (court_dept)
try:
    c.execute("SELECT COUNT(*) FROM auction_items WHERE court_code IS NOT NULL AND court_code != ''")
    print(f'  court_code 있음: {c.fetchone()[0]:,}건')
except: pass

# 3. 토지이용계획 개선 여부
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%토지이용계획%'")
print(f'  appraisal_report에 토지이용계획 언급: {c.fetchone()[0]:,}건')

# 4. 지붕구조 개선
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%지붕%'")
print(f'  appraisal_report에 지붕 언급: {c.fetchone()[0]:,}건')

# 5. 층수 개선
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%층 건물%'")
print(f'  appraisal_report에 층 건물 언급: {c.fetchone()[0]:,}건')

# 6. 사용승인일
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%사용승인%' OR appraisal_report LIKE '%사용검사%'")
print(f'  appraisal_report에 사용승인/검사 언급: {c.fetchone()[0]:,}건')

# 7. 연면적
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%연면적%'")
print(f'  appraisal_report에 연면적 언급: {c.fetchone()[0]:,}건')

# 8. 건폐율/용적률
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%건폐율%' OR appraisal_report LIKE '%용적률%'")
print(f'  appraisal_report에 건폐율/용적률 언급: {c.fetchone()[0]:,}건')

# 9. 주차대수
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%주차%'")
print(f'  appraisal_report에 주차 언급: {c.fetchone()[0]:,}건')

# 10. 대지권
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%대지권%'")
print(f'  appraisal_report에 대지권 언급: {c.fetchone()[0]:,}건')

# 11. 분양/관리비
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%관리비%'")
print(f'  appraisal_report에 관리비 언급: {c.fetchone()[0]:,}건')

# 12. 도로 접면
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%도로%' AND appraisal_report LIKE '%접%'")
print(f'  appraisal_report에 도로접면 언급: {c.fetchone()[0]:,}건')

# 13. 세대수
c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report LIKE '%세대%'")
print(f'  appraisal_report에 세대 언급: {c.fetchone()[0]:,}건')

conn.close()