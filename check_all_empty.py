import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# 테이블 스키마 확인
c.execute("PRAGMA table_info(auction_items)")
columns = [row[1] for row in c.fetchall()]
print("=== DB 컬럼 목록 ===")
print(f"총 {len(columns)}개 컬럼")
for col in columns:
    print(f"  {col}")

print(f"\n=== 전체 건수: 32,614건 ===\n")

# 각 컬럼별 빈값 통계
print("=== 컬럼별 빈값/NULL 현황 ===")
for col in columns:
    c.execute(f"SELECT COUNT(*) FROM auction_items WHERE {col} IS NULL OR {col} = '' OR {col} = 0")
    empty = c.fetchone()[0]
    if empty > 0:
        c.execute(f"SELECT COUNT(*) FROM auction_items WHERE {col} IS NOT NULL AND {col} != '' AND {col} != 0")
        has_val = c.fetchone()[0]
        print(f"  {col:30s} → 빈값: {empty:>6,} / 값있음: {has_val:>6,}")

# 샘플 데이터 1건
print("\n=== 샘플 데이터 (1건) ===")
c.execute("SELECT * FROM auction_items LIMIT 1")
row = c.fetchone()
for col, val in zip(columns, row):
    print(f"  {col:30s} = {repr(val)[:80]}")