import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# Get one completed item with details
c.execute('''SELECT internal_id, case_number, court, item_type, category, address, address_sido,
             appraisal_price, min_price, sale_price, status, auction_type,
             creditor, debtor, owner, claim_amount, deposit,
             land_area, building_area, building_structure, total_floors, target_floor,
             heating_type, parking_available, elevator_available,
             fail_count, sale_date, min_rate, sale_rate
             FROM auction_items WHERE detail_scraped=1 LIMIT 1''')
row = c.fetchone()
if row:
    cols = ['internal_id','case_number','court','item_type','category','address','address_sido',
            'appraisal_price','min_price','sale_price','status','auction_type',
            'creditor','debtor','owner','claim_amount','deposit',
            'land_area','building_area','building_structure','total_floors','target_floor',
            'heating_type','parking_available','elevator_available',
            'fail_count','sale_date','min_rate','sale_rate']
    for col, val in zip(cols, row):
        print(f'  {col}: {val}')

    # Check related tables
    internal_id = row[0]
    c.execute('SELECT COUNT(*) FROM auction_bid_history WHERE internal_id=?', (internal_id,))
    print(f'  bid_history_count: {c.fetchone()[0]}')
    c.execute('SELECT COUNT(*) FROM auction_tenants WHERE internal_id=?', (internal_id,))
    print(f'  tenants_count: {c.fetchone()[0]}')
    c.execute('SELECT COUNT(*) FROM auction_documents WHERE internal_id=?', (internal_id,))
    print(f'  documents_count: {c.fetchone()[0]}')

# Summary stats
print('\n--- Summary ---')
c.execute('SELECT category, COUNT(*) FROM auction_items WHERE detail_scraped=1 GROUP BY category ORDER BY COUNT(*) DESC')
for cat, cnt in c.fetchall():
    print(f'  {cat or "none"}: {cnt}')

c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND appraisal_report != "" AND appraisal_report IS NOT NULL')
print(f'\n  appraisal_report: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND status_report != "" AND status_report IS NOT NULL')
print(f'  status_report: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND sale_statement != "" AND sale_statement IS NOT NULL')
print(f'  sale_statement: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND property_list != "" AND property_list IS NOT NULL')
print(f'  property_list: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND delivery_records != "" AND delivery_records IS NOT NULL')
print(f'  delivery_records: {c.fetchone()[0]}')

conn.close()