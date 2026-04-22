import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM auction_items')
total = c.fetchone()[0]
print(f'Total items: {total}')

c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1')
print(f'Detail scraped: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_report IS NOT NULL AND appraisal_report != ''")
print(f'appraisal_report filled: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM auction_items WHERE status_report IS NOT NULL AND status_report != ''")
print(f'status_report filled: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM auction_items WHERE building_structure IS NOT NULL AND building_structure != ''")
print(f'building_structure filled: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM auction_items WHERE claim_deadline IS NOT NULL AND claim_deadline != ''")
print(f'claim_deadline filled: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM auction_items WHERE appraisal_summary IS NOT NULL AND appraisal_summary != ''")
print(f'appraisal_summary filled: {c.fetchone()[0]}')

c.execute('SELECT COUNT(*) FROM auction_tenants')
print(f'auction_tenants rows: {c.fetchone()[0]}')

c.execute('SELECT COUNT(*) FROM auction_documents')
print(f'auction_documents rows: {c.fetchone()[0]}')

conn.close()