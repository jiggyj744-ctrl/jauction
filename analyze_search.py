"""
gfauction.co.kr 검색 결과 페이지 구조 분석 스크립트
search/search_list.php 페이지의 HTML 구조를 분석합니다.
"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import json

# 세션 설정
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    'Referer': 'https://gfauction.co.kr/main/main.php'
})

# 1. 메인 검색 페이지 (2026년 전체)
print("=" * 60)
print("1. 검색 결과 페이지 분석 (2026년)")
print("=" * 60)

url = 'https://gfauction.co.kr/search/search_list.php'
params = {
    'aresult': 'all',
    'sno': '2026'
}

try:
    resp = session.get(url, params=params, timeout=15)
    print(f"Status: {resp.status_code}")
    print(f"Content-Length: {len(resp.text)} bytes")
    
    # HTML 저장
    with open(r'C:\Users\Work\Desktop\gfauction\data\search_list_2026.html', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print("HTML saved to search_list_2026.html")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 테이블 찾기
    tables = soup.find_all('table')
    print(f"\nTables found: {len(tables)}")
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"  Table {i}: {len(rows)} rows")
        if len(rows) > 0:
            # 헤더 확인
            header = rows[0]
            ths = header.find_all('th')
            tds = header.find_all('td')
            if ths:
                print(f"    Headers (th): {[th.get_text(strip=True) for th in ths]}")
            if tds:
                print(f"    Headers (td): {[td.get_text(strip=True) for td in tds[:10]]}")
    
    # 리스트 구조 찾기 (div, ul 등)
    print("\n--- Div classes found ---")
    divs_with_class = soup.find_all('div', class_=True)
    for div in divs_with_class[:30]:
        cls = ' '.join(div.get('class', []))
        print(f"  div.{cls}")
    
    # 링크 패턴 분석 (경매 물건 상세 페이지 링크)
    print("\n--- Link patterns ---")
    links = soup.find_all('a', href=True)
    detail_links = [a for a in links if 'search' in a.get('href', '').lower() or 'detail' in a.get('href', '').lower() or 'view' in a.get('href', '').lower()]
    print(f"Total links: {len(links)}")
    print(f"Detail-like links: {len(detail_links)}")
    for link in detail_links[:10]:
        print(f"  {link.get('href')} -> {link.get_text(strip=True)[:50]}")
    
    # 폼 분석
    print("\n--- Forms ---")
    forms = soup.find_all('form')
    for i, form in enumerate(forms):
        print(f"  Form {i}: action={form.get('action')} method={form.get('method')}")
        inputs = form.find_all('input')
        for inp in inputs[:10]:
            print(f"    input: name={inp.get('name')} type={inp.get('type')} value={inp.get('value', '')[:30]}")
    
    # 페이징 확인
    print("\n--- Pagination ---")
    paging = soup.find_all('a', href=True)
    page_links = [a for a in paging if 'page' in a.get('href', '').lower()]
    for pl in page_links[:10]:
        print(f"  {pl.get('href')} -> {pl.get_text(strip=True)[:30]}")

except Exception as e:
    print(f"Error: {e}")

# 2. 상세 검색 페이지 분석 (search01.php)
print("\n" + "=" * 60)
print("2. 검색 폼 페이지 분석 (search01.php)")
print("=" * 60)

try:
    resp2 = session.get('https://gfauction.co.kr/search/search01.php', timeout=15)
    print(f"Status: {resp2.status_code}")
    
    with open(r'C:\Users\Work\Desktop\gfauction\data\search01.html', 'w', encoding='utf-8') as f:
        f.write(resp2.text)
    
    soup2 = BeautifulSoup(resp2.text, 'html.parser')
    forms2 = soup2.find_all('form')
    for i, form in enumerate(forms2):
        print(f"  Form {i}: action={form.get('action')} method={form.get('method')}")
        selects = form.find_all('select')
        for sel in selects:
            options = sel.find_all('option')
            print(f"    select name={sel.get('name')}: {[o.get('value') for o in options[:5]]}...")
        inputs2 = form.find_all('input')
        for inp in inputs2[:10]:
            print(f"    input: name={inp.get('name')} type={inp.get('type')} value={str(inp.get('value', ''))[:30]}")

except Exception as e:
    print(f"Error: {e}")

print("\n✅ 분석 완료!")