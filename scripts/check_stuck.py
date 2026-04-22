import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

# When did scraping stop?
for t in ['01:44', '02:00', '02:15', '02:30', '02:40', '02:45', '02:48', '02:49']:
    c.execute("SELECT COUNT(*) FROM auction_items WHERE detail_scraped=1 AND updated_at >= '2026-04-21 " + t + ":00'")
    print(f"  after {t}: {c.fetchone()[0]}")

# Check for errors in recent items
print("\n--- Last 10 updated ---")
c.execute("SELECT internal_id, updated_at FROM auction_items WHERE detail_scraped=1 ORDER BY updated_at DESC LIMIT 10")
for row in c.fetchall():
    print(f"  ID:{row[0]} at {row[1]}")

# Check items that might be stuck (not scraped, processed recently)  
print("\n--- Unscraped count ---")
c.execute("SELECT COUNT(*) FROM auction_items WHERE detail_scraped=0 OR detail_scraped IS NULL")
print(f"  remaining: {c.fetchone()[0]}")

conn.close()