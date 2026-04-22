import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != ''")
print('pdf_urls filled:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != '' AND detail_scraped=0")
print('pdf_urls in pending items:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != '' AND detail_scraped=1")
print('pdf_urls in scraped items:', c.fetchone()[0])

c.execute("SELECT pdf_urls FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != '' LIMIT 3")
rows = c.fetchall()
print('\nSamples:')
for r in rows:
    print(r[0][:200])
    print('---')

conn.close()