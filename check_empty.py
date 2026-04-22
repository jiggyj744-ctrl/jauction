import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# 해당 건 조회
c.execute("SELECT case_number, auction_type, fail_count FROM auction_items WHERE case_number LIKE '%2022-2701%'")
print('=== 해당 건 ===')
for r in c.fetchall(): print(r)

# 경매종류 통계
print('\n=== 경매종류 통계 ===')
c.execute("SELECT COUNT(*) FROM auction_items WHERE auction_type IS NULL OR auction_type = ''")
print(f'빈값: {c.fetchone()[0]:,}')
c.execute("SELECT auction_type, COUNT(*) FROM auction_items WHERE auction_type IS NOT NULL AND auction_type != '' GROUP BY auction_type")
for r in c.fetchall(): print(f'  {r[0]}: {r[1]:,}')

# 유찰횟수 통계
print('\n=== 유찰횟수 통계 ===')
c.execute("SELECT COUNT(*) FROM auction_items WHERE fail_count IS NULL OR fail_count = 0")
print(f'빈값/0: {c.fetchone()[0]:,}')
c.execute("SELECT fail_count, COUNT(*) FROM auction_items WHERE fail_count > 0 GROUP BY fail_count ORDER BY fail_count")
for r in c.fetchall(): print(f'  {r[0]}회: {r[1]:,}')

# detail_scraped 여부
print('\n=== detail_scraped ===')
c.execute("SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1")
print(f'스크랩됨: {c.fetchone()[0]:,}')
c.execute("SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 0 OR detail_scraped IS NULL")
print(f'미스크랩: {c.fetchone()[0]:,}')