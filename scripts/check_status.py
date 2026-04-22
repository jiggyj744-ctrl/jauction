import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM auction_items')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1')
done = c.fetchone()[0]
c.execute('SELECT updated_at FROM auction_items WHERE detail_scraped=1 ORDER BY updated_at DESC LIMIT 1')
r = c.fetchone()
print(f'total={total} done={done} remain={total-done} last_update={r[0] if r else "none"}')
conn.close()