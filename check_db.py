import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# 부동산 물건 상세 (차량/중장비 제외)
c.execute("""SELECT internal_id, case_number, court, item_type, category, address, status, sale_date,
appraisal_price, min_price, sale_price, min_rate, sale_rate, auction_type,
creditor, debtor, owner, land_area, building_area, claim_amount, deposit,
summary, notes, related_case, tenant_info, non_extinguishable_rights,
detail_scraped
FROM auction_items WHERE item_type NOT IN ('차량','중장비') LIMIT 10""")
rows = c.fetchall()
col_names = [d[0] for d in c.description]

print("=== 부동산 물건 상세 (차량/중장비 제외) ===")
for row in rows:
    print("=" * 80)
    for name, val in zip(col_names, row):
        if val:
            print(f"  {name}: {val}")
    print()

print()
print("=== 전체 통계 ===")
c.execute("SELECT COUNT(*) FROM auction_items")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM auction_items WHERE item_type NOT IN ('차량','중장비')")
estate = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM auction_items WHERE status IN ('신건','유찰','변경')")
active = c.fetchone()[0]

excluded = total - active
print(f"  전체: {total}건")
print(f"  부동산: {estate}건")
print(f"  활성(신건/유찰/변경): {active}건")
print(f"  제외예정(취하/기각/정지/매각): {excluded}건")

# 이미지 확인
c.execute("SELECT COUNT(*) FROM auction_images")
imgs = c.fetchone()[0]
print(f"  저장된 이미지: {imgs}장")

# 제외 후 남을 물건
print()
print("=== 필터 후 남을 물건 ===")
c.execute("""SELECT status, COUNT(*) FROM auction_items 
WHERE item_type NOT IN ('차량','중장비','묘지') 
AND status NOT IN ('취하','기각','정지','매각')
GROUP BY status""")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}건")

c.execute("""SELECT COUNT(*) FROM auction_items 
WHERE item_type NOT IN ('차량','중장비','묘지') 
AND status NOT IN ('취하','기각','정지','매각')""")
final = c.fetchone()[0]
print(f"  최종 수집 대상: {final}건")

conn.close()