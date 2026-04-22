"""
gfauction.co.kr 상세 페이지 분석 후 전체 크롤러 업데이트
"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re
import sqlite3
import time
import os

BASE_URL = 'https://gfauction.co.kr'
DB_PATH = r'C:\Users\Work\Desktop\gfauction\data\auction.db'

# ==========================================
# 1. 로그인
# ==========================================
print("=" * 60)
print("1. 로그인")
print("=" * 60)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
})

login_page_url = f'{BASE_URL}/member/member01.php'
session.get(login_page_url, timeout=15)

encoded_id = base64.b64encode('1111'.encode('utf-8')).decode('utf-8')
encoded_pw = base64.b64encode('1111'.encode('utf-8')).decode('utf-8')

resp = session.post(f'{BASE_URL}/member/login_proc.php', data={
    'rtn_page': '', 'id': encoded_id, 'pwd': encoded_pw, 'login_id': '', 'login_pw': ''
}, timeout=15, headers={'Referer': login_page_url, 'Origin': BASE_URL})

resp_check = session.get(f'{BASE_URL}/main/main.php', timeout=15)
if '로그아웃' in resp_check.text:
    print("✅ 로그인 성공!")
else:
    print("❌ 로그인 실패")
    exit()

# ==========================================
# 2. 상세 페이지 분석 (첫 번째 물건)
# ==========================================
print("\n" + "=" * 60)
print("2. 상세 페이지 분석")
print("=" * 60)

detail_url = f'{BASE_URL}/search/detail_view.php?idx=1479080'
resp_d = session.get(detail_url, timeout=15)
print(f"Status: {resp_d.status_code}, Length: {len(resp_d.text)}")

with open(r'C:\Users\Work\Desktop\gfauction\data\detail_sample.html', 'w', encoding='utf-8') as f:
    f.write(resp_d.text)

soup_d = BeautifulSoup(resp_d.text, 'html.parser')

# 모든 테이블 분석
tables = soup_d.find_all('table')
print(f"\n테이블 수: {len(tables)}")

detail_data = {}
for ti, table in enumerate(tables):
    cls = ' '.join(table.get('class', []))
    rows = table.find_all('tr')
    if len(rows) > 0:
        print(f"\n=== Table {ti} (class={cls}, rows={len(rows)}) ===")
        for ri, row in enumerate(rows[:60]):
            ths = row.find_all('th')
            tds = row.find_all('td')
            if ths or tds:
                th_text = [th.get_text(strip=True)[:50] for th in ths]
                td_text = [td.get_text(strip=True)[:80] for td in tds]
                if any(t for t in th_text) or any(t for t in td_text):
                    print(f"  [{ri}] th={th_text} | td={td_text}")
                    # key-value 형태면 저장
                    if len(th_text) == 1 and len(td_text) == 1:
                        key = th_text[0].strip()
                        val = td_text[0].strip()
                        if key and val:
                            detail_data[key] = val

print(f"\n\n추출된 상세 데이터:")
for k, v in detail_data.items():
    print(f"  {k}: {v}")

# ==========================================
# 3. 검색 결과 리스트 파싱 테스트
# ==========================================
print("\n" + "=" * 60)
print("3. 검색 결과 리스트 파싱")
print("=" * 60)

list_url = f'{BASE_URL}/search/search_list.php'
params = {'aresult': 'all', 'sno': '2026', 'rows': '20'}
resp3 = session.get(list_url, params=params, timeout=15)
soup3 = BeautifulSoup(resp3.text, 'html.parser')

table = soup3.find('table', class_='tbl_list')
if table:
    rows = table.find_all('tr')
    items = []
    
    for row in rows:
        if row.find('th'):
            continue
        
        chk = row.find('input', {'name': 'aChk'})
        if not chk:
            continue
        
        item = {}
        item['internal_id'] = chk.get('value')
        
        # 사진 URL
        img = row.find('img')
        if img:
            item['photo_url'] = img.get('src', '')
        
        # onclick에서 detail_view 링크
        first_td = row.find('td', onclick=True)
        if first_td:
            onclick_text = first_td.get('onclick', '')
            match = re.search(r"detail_view\.php\?idx=(\d+)", onclick_text)
            if match:
                item['detail_idx'] = match.group(1)
        
        # ul 구조에서 데이터 추출
        uls = row.find_all('ul')
        for ul in uls:
            lis = ul.find_all('li')
            li_classes = [li.get('class', []) for li in lis]
            li_texts = [li.get_text(strip=True) for li in lis]
            
            cls = ' '.join(ul.get('class', []))
            
            if 'list_sell01' in cls:
                # 날짜, 구분, 법원, 물건종류
                if len(li_texts) >= 4:
                    item['sale_date'] = li_texts[0]
                    item['court'] = li_texts[2]
                    item['item_type'] = li_texts[3]
            elif 'list_sell02' in cls:
                # 사건번호, 주소
                if len(li_texts) >= 2:
                    item['case_number'] = li_texts[0]
                    item['address'] = li_texts[1]
            elif 'list_sell03' in cls:
                # 감정가, 최저가, 매각가
                for li_idx, (cls_list, text) in enumerate(zip(li_classes, li_texts)):
                    if 'lest_test03' in cls_list:
                        item['appraisal_price'] = text
                    elif 'lest_test04' in cls_list:
                        item['min_price'] = text
                    elif 'lest_test07' in cls_list:
                        item['sale_price'] = text
            elif 'list_sell01' in cls and 'lest_test03' in str(li_classes):
                # 상태, 비율
                for cls_list, text in zip(li_classes, li_texts):
                    if 'lest_test03' in cls_list:
                        item['status'] = text
                    elif 'lest_test04' in cls_list:
                        item['min_rate'] = text
                    elif 'lest_test07' in cls_list:
                        item['sale_rate'] = text
        
        # 조회수
        last_td = row.find_all('td')
        if last_td:
            last_text = last_td[-1].get_text(strip=True)
            if last_text.isdigit():
                item['views'] = int(last_text)
        
        items.append(item)
        
        if len(items) <= 3:
            print(f"\n물건 {len(items)}: {item.get('case_number', '?')}")
            for k, v in item.items():
                print(f"  {k}: {v}")
    
    print(f"\n총 {len(items)}개 물건 파싱됨")

print("\n✅ 분석 완료")