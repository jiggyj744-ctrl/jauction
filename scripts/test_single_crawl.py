"""단일 물건 크롤링 테스트 (수정된 파서 검증)"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

from crawler import *
import sqlite3

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
})
login(session)

# Test with ID 1447465
TEST_ID = '1447465'
print(f'\n=== 파싱 테스트 ID={TEST_ID} ===')
detail = parse_detail_page(session, TEST_ID)

if detail:
    summary = detail.get('appraisal_summary', '') or ''
    report = detail.get('appraisal_report', '') or ''
    status = detail.get('status_report', '') or ''
    pdfs = detail.get('pdf_urls', [])
    sale = detail.get('sale_statement', '') or ''
    prop = detail.get('property_list', '') or ''
    delivery = detail.get('delivery_records', '') or ''
    docs = detail.get('documents', [])
    tenants = detail.get('tenants', [])
    bids = detail.get('bid_history', [])
    
    print(f'appraisal_summary: {summary[:120]}...')
    print(f'appraisal_report: {len(report)} chars')
    print(f'status_report: {len(status)} chars')
    print(f'pdf_urls: {pdfs}')
    print(f'sale_statement: {len(sale)} chars')
    print(f'property_list: {len(prop)} chars')
    print(f'delivery_records: {len(delivery)} chars')
    print(f'documents: {len(docs)}건')
    print(f'tenants: {len(tenants)}건')
    print(f'bid_history: {len(bids)}건')
    print(f'building_structure: {detail.get("building_structure", "")}')
    print(f'claim_deadline: {detail.get("claim_deadline", "")}')
    
    # DB 저장
    detail['fail_count'] = sum(1 for b in bids if '유찰' in b.get('result', ''))
    result = save_detail_to_db(detail)
    print(f'\nDB 저장: {"성공" if result else "실패"}')
    
    # DB 확인
    conn = sqlite3.connect('data/auction.db')
    c = conn.cursor()
    c.execute('''SELECT appraisal_summary, appraisal_report, pdf_urls, 
                        sale_statement, property_list, delivery_records,
                        status_report, detail_scraped
                 FROM auction_items WHERE internal_id = ?''', (TEST_ID,))
    row = c.fetchone()
    if row:
        print(f'\n=== DB 확인 ===')
        print(f'appraisal_summary: {(row[0] or "")[:120]}...')
        print(f'appraisal_report: {len(row[1] or "")} chars')
        print(f'pdf_urls: {row[2] or ""}')
        print(f'sale_statement: {len(row[3] or "")} chars')
        print(f'property_list: {len(row[4] or "")} chars')
        print(f'delivery_records: {len(row[5] or "")} chars')
        print(f'status_report: {len(row[6] or "")} chars')
        print(f'detail_scraped: {row[7]}')
    
    # documents 확인
    c.execute('SELECT COUNT(*) FROM auction_documents WHERE internal_id = ?', (TEST_ID,))
    doc_count = c.fetchone()[0]
    print(f'auction_documents: {doc_count}건')
    
    c.execute('SELECT COUNT(*) FROM auction_tenants WHERE internal_id = ?', (TEST_ID,))
    tenant_count = c.fetchone()[0]
    print(f'auction_tenants: {tenant_count}건')
    
    c.execute('SELECT COUNT(*) FROM auction_bid_history WHERE internal_id = ?', (TEST_ID,))
    bid_count = c.fetchone()[0]
    print(f'auction_bid_history: {bid_count}건')
    
    conn.close()
    print('\n테스트 완료!')
else:
    print('파싱 실패!')