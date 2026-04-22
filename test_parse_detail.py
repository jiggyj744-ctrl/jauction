"""부동산 상세페이지 전체 필드 파싱 테스트 v2"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import requests
from bs4 import BeautifulSoup
import base64
import re
import json
import webbrowser
import os

BASE_URL = 'https://gfauction.co.kr'

def clean(text):
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).replace('\xa0', ' ').strip()

# 로그인
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})

print("[1] 로그인 중...")
login_page = f'{BASE_URL}/member/member01.php'
session.get(login_page, timeout=15)

encoded_id = base64.b64encode(b'1111').decode()
encoded_pw = base64.b64encode(b'1111').decode()

session.post(f'{BASE_URL}/member/login_proc.php', data={
    'rtn_page': '', 'id': encoded_id, 'pwd': encoded_pw,
    'login_id': '', 'login_pw': '',
}, timeout=15, headers={'Referer': login_page, 'Origin': BASE_URL})

check = session.get(f'{BASE_URL}/main/main.php', timeout=15)
if '로그아웃' not in check.text:
    print("로그인 실패!")
    exit()
print("로그인 성공!")

# DB에서 오피스텔 internal_id
import sqlite3
conn = sqlite3.connect('data/auction.db')
c = conn.cursor()
c.execute("SELECT internal_id, case_number, court, item_type FROM auction_items WHERE item_type = '오피스텔' LIMIT 1")
row = c.fetchone()
conn.close()

if not row:
    print("오피스텔 물건 없음")
    exit()

internal_id, case_number, court, item_type = row
print(f"\n[2] 파싱 대상: {case_number} ({court} / {item_type}) ID:{internal_id}")

# 상세 페이지
detail_url = f'{BASE_URL}/search/detail_view.php?idx={internal_id}'
resp = session.get(detail_url, timeout=15)
print(f"상세페이지 크기: {len(resp.text)} bytes")

soup = BeautifulSoup(resp.text, 'html.parser')
result = {}

# ==========================================
# 1. 헤더 (#dtb_sum)
# ==========================================
dtb_sum = soup.find('div', id='dtb_sum')
if dtb_sum:
    for li in dtb_sum.find_all('li'):
        cls = ' '.join(li.get('class', []))
        text = clean(li.get_text())
        if 'dtb01' in cls: result['법원전체명'] = text
        elif 'dtb02' in cls: result['경매계'] = text
        elif 'dtb03' in cls: result['사건번호전체'] = text
        elif 'dtb05' in cls: result['매각일시'] = text
print(f"  헤더: {len(result)}개")

# ==========================================
# 2. 기본 정보 테이블 (#table_sum)
# ==========================================
table_sum = soup.find('div', id='table_sum')
if table_sum:
    for tr in table_sum.find_all('tr'):
        th_elems = tr.find_all('th')
        td_elems = tr.find_all('td')
        ths = [clean(th.get_text()) for th in th_elems]
        tds_text = [clean(td.get_text()) for td in td_elems]
        
        for i, th in enumerate(ths):
            td_val = tds_text[i] if i < len(tds_text) else ''
            td_val = td_val.replace('대법원바로가기', '').strip()
            
            key_map = {
                '소재지': '소재지', '물건종류': '물건종류', '채권자': '채권자',
                '경매대상': '경매대상', '채무자': '채무자', '토지면적': '토지면적',
                '소유자': '소유자', '건물면적': '건물면적', '감정가': '감정가',
                '경매종류': '경매종류', '최저가': '최저가', '청구금액': '청구금액',
                '보증금': '보증금',
            }
            if th in key_map:
                result[key_map[th]] = td_val
print(f"  기본정보: {len(result)}개")

# ==========================================
# 3. 관련사건 (별도 테이블)
# ==========================================
for table in soup.find_all('table', class_='tbl_dtb'):
    for tr in table.find_all('tr'):
        ths = [clean(th.get_text()) for th in tr.find_all('th')]
        tds_text = [clean(td.get_text()) for td in tr.find_all('td')]
        for th, td in zip(ths, tds_text):
            if '관련사건' in th:
                result['관련사건'] = td.replace('사건검색', '').replace('이송전사건사건검색', '').strip()

# ==========================================
# 4. 입찰이력
# ==========================================
bid_history = []
history_div = soup.find('div', id='hisdiv')
if history_div:
    htable = history_div.find('table', class_='tbl_dtb_history')
    if htable:
        for tr in htable.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 4:
                td0 = clean(tds[0].get_text())
                if td0 and '입찰기일' not in td0:
                    bid_history.append({
                        '회차': td0,
                        '입찰기일': clean(tds[1].get_text()),
                        '최저입찰금액': clean(tds[2].get_text()),
                        '결과': clean(tds[3].get_text()),
                    })
            elif len(tds) == 1 and bid_history:
                text = clean(tds[0].get_text())
                if '낙찰가' in text:
                    bid_history[-1]['낙찰가'] = text
result['입찰이력'] = bid_history
print(f"  입찰이력: {len(bid_history)}건")

# ==========================================
# 5. 전체 이미지 (메인 + 팝업)
# ==========================================
photo_urls = []

# 5a. #dtb_pic에서 보이는 이미지
dtb_pic = soup.find('div', id='dtb_pic')
if dtb_pic:
    for img in dtb_pic.find_all('img'):
        src = img.get('src', '')
        if src and 'sample_img' not in src:
            photo_urls.append(src)
print(f"  메인 이미지: {len(photo_urls)}장")

# 5b. 팝업에서 추가 이미지 시도
popup_url = f'{BASE_URL}/search/pop_detail.php?gubun=pic_0.jpg&idx={internal_id}'
try:
    popup_resp = session.get(popup_url, timeout=10)
    if popup_resp.status_code == 200 and len(popup_resp.text) > 500:
        popup_soup = BeautifulSoup(popup_resp.text, 'html.parser')
        for img in popup_soup.find_all('img'):
            src = img.get('src', '')
            if src and 'nuriauction' in src and src not in photo_urls:
                photo_urls.append(src)
        # bxslider 이미지도 확인
        for li in popup_soup.find_all('li'):
            img = li.find('img')
            if img:
                src = img.get('src', '')
                if src and 'nuriauction' in src and src not in photo_urls:
                    photo_urls.append(src)
        print(f"  팝업 이미지 추가: 총 {len(photo_urls)}장")
    else:
        print(f"  팝업 없음 (HTTP {popup_resp.status_code})")
except Exception as e:
    print(f"  팝업 오류: {e}")

result['물건사진'] = photo_urls

# ==========================================
# 6. 감정평가현황 (h3 기준으로 섹션 찾기)
# ==========================================
h3_tags = soup.find_all('h3')
appraisal_list = []

for h3 in h3_tags:
    if '감정평가현황' not in h3.get_text():
        continue
    
    form_div = h3.find_parent('div', id='dtb_form')
    if not form_div:
        continue
    
    tbl = form_div.find('table', class_='tbl_dtb')
    if not tbl:
        continue
    
    for tr in tbl.find_all('tr'):
        th_elems = tr.find_all('th')
        td_elems = tr.find_all('td')
        ths = [clean(th.get_text()) for th in th_elems]
        tds = [clean(td.get_text()) for td in td_elems]
        
        # 헤더행 (목록, 주소, 구조/용도/대지권, 면적, 비고)
        if any('목록' in t for t in ths):
            continue
        
        # 차량정보 (th 3개 + td 3개)
        if len(ths) == 3 and len(tds) == 3:
            for th, td in zip(ths, tds):
                if th.strip() and td.strip():
                    result[f'감정_{th.strip()}'] = td.strip()
        
        # 요약 행
        elif len(tds) >= 2 and tds[0] == '요약':
            judDiv = tr.find('div', id='judDiv')
            if judDiv:
                result['요약'] = clean(judDiv.get_text())
            else:
                result['요약'] = tds[-1] if len(tds) > 1 else ''
        
        # 참고사항 행
        elif len(tds) >= 2 and tds[0] == '참고사항':
            result['참고사항_감정'] = tds[-1] if len(tds) > 1 else ''
        
        # 부동산 목록 행 (대지권, 건물, 제시외건물 등)
        elif len(td_elems) >= 3 and not th_elems:
            entry = {
                '목록': clean(td_elems[0].get_text()),
                '주소': clean(td_elems[1].get_text()) if len(td_elems) > 1 else '',
                '구조용도대지권': clean(td_elems[2].get_text()) if len(td_elems) > 2 else '',
                '면적': clean(td_elems[3].get_text()) if len(td_elems) > 3 else '',
                '비고': clean(td_elems[4].get_text()) if len(td_elems) > 4 else '',
            }
            appraisal_list.append(entry)
    
    break  # 첫 번째 감정평가현황만

result['감정평가목록'] = appraisal_list
print(f"  감정평가목록: {len(appraisal_list)}건, 요약: {'O' if result.get('요약') else 'X'}")

# ==========================================
# 7. 임차인현황
# ==========================================
tenants = []
claim_deadline = ''

for h3 in h3_tags:
    if '임차인' not in h3.get_text():
        continue
    
    # 배당요구종기
    title_div = h3.find_parent('div', id='dtbf_title')
    if title_div:
        p = title_div.find('p')
        if p:
            claim_deadline = clean(p.get_text())
    
    # 임차인 테이블
    form_div = h3.find_parent('div', id='dtb_form')
    if form_div:
        tbl = form_div.find('table', class_='tbl_dtb')
        if tbl:
            for tr in tbl.find_all('tr'):
                td_elems = tr.find_all('td')
                if len(td_elems) >= 6:
                    tenant = {
                        '임차인': clean(td_elems[0].get_text()),
                        '용도점유': clean(td_elems[1].get_text()),
                        '전입일자': clean(td_elems[2].get_text()) if len(td_elems) > 2 else '',
                        '확정일자': clean(td_elems[3].get_text()) if len(td_elems) > 3 else '',
                        '배당요구일': clean(td_elems[4].get_text()) if len(td_elems) > 4 else '',
                        '보증금월세': clean(td_elems[5].get_text()) if len(td_elems) > 5 else '',
                    }
                    tenants.append(tenant)
                elif len(td_elems) == 1:
                    text = clean(td_elems[0].get_text())
                    if '조사된 임차' not in text and text:
                        tenants.append({'내용': text})
                elif len(td_elems) >= 2:
                    label = clean(td_elems[0].get_text())
                    val = clean(td_elems[1].get_text())
                    if label and val:
                        tenants.append({label: val})
    break

result['배당요구종기'] = claim_deadline
result['임차인현황'] = tenants
print(f"  임차인: {len(tenants)}건, 배당요구종기: {claim_deadline}")

# ==========================================
# 8. 건물 등기부현황
# ==========================================
register = []

for h3 in h3_tags:
    if '등기부' not in h3.get_text():
        continue
    
    form_div = h3.find_parent('div', id='dtb_form')
    if not form_div:
        continue
    
    tbl = form_div.find('table', class_='tbl_dtb')
    if not tbl:
        continue
    
    for tr in tbl.find_all('tr'):
        td_elems = tr.find_all('td')
        th_elems = tr.find_all('th')
        
        # 데이터 행 (td 6개, th 0개)
        if len(td_elems) == 6 and len(th_elems) == 0:
            entry = {
                '구분': clean(td_elems[0].get_text()),
                '성립일자': clean(td_elems[1].get_text()),
                '권리': clean(td_elems[2].get_text()),
                '권리자': clean(td_elems[3].get_text()),
                '권리금액': clean(td_elems[4].get_text()),
                '인수소멸': clean(td_elems[5].get_text()),
            }
            register.append(entry)
    break

result['등기부현황'] = register
print(f"  등기부현황: {len(register)}건")

# ==========================================
# 9. 주의사항
# ==========================================
for h3 in h3_tags:
    if '주의사항' not in h3.get_text():
        continue
    
    form_div = h3.find_parent('div', id='dtb_form')
    if not form_div:
        continue
    
    tbl = form_div.find('table', class_='tbl_dtb')
    if not tbl:
        continue
    
    for tr in tbl.find_all('tr'):
        ths = [clean(th.get_text()) for th in tr.find_all('th')]
        tds = [clean(td.get_text()) for td in tr.find_all('td')]
        for th, td in zip(ths, tds):
            if '소멸되지 않는 등기부권리' in th:
                result['소멸되지않는등기부권리'] = td
            elif '소멸되지 않는 지상권' in th:
                result['소멸되지않는지상권'] = td
            elif th == '주의사항':
                result['주의사항'] = td
    break

print(f"  주의사항: {'O' if result.get('소멸되지않는등기부권리') else 'X'}")

# ==========================================
# 10. 인근매각통계
# ==========================================
stats = {}

for h3 in h3_tags:
    if '인근매각통계' not in h3.get_text():
        continue
    
    form_div = h3.find_parent('div', id='dtb_form')
    if not form_div:
        continue
    
    tbl = form_div.find('table', class_='tbl_dtb')
    if not tbl:
        continue
    
    for tr in tbl.find_all('tr'):
        td_elems = tr.find_all('td')
        if len(td_elems) >= 5:
            period = clean(td_elems[0].get_text())
            if '개월' in period:
                stats[period] = {
                    '낙찰물건수': clean(td_elems[1].get_text()),
                    '평균감정가': clean(td_elems[2].get_text()),
                    '평균낙찰가': clean(td_elems[3].get_text()),
                    '유찰횟수': clean(td_elems[4].get_text()),
                }
    break

result['인근매각통계'] = stats
print(f"  인근매각통계: {len(stats)}개 기간")

# ==========================================
# 결과 출력
# ==========================================
total_fields = len([k for k, v in result.items() if not isinstance(v, (list, dict))])
total_fields += len(result.get('입찰이력', []))
total_fields += len(result.get('감정평가목록', []))
total_fields += len(result.get('임차인현황', []))
total_fields += len(result.get('등기부현황', []))
total_fields += len(result.get('인근매각통계', {}))
total_fields += len(result.get('물건사진', []))
print(f"\n  총 파싱 데이터: {total_fields}개")

# ==========================================
# HTML 생성
# ==========================================
html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>전체 파싱 결과 - """ + case_number + """</title>
<style>
body { font-family: 'Malgun Gothic', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
h1 { color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }
.section { background: #fff; border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.section h2 { font-size: 16px; color: #37474F; margin-bottom: 12px; border-left: 4px solid #2196F3; padding-left: 10px; }
table { width: 100%; border-collapse: collapse; }
th { background: #37474F; color: #fff; padding: 8px 12px; font-size: 13px; text-align: left; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; }
td.label { font-weight: bold; color: #555; background: #fafafa; width: 170px; }
tr:nth-child(even) td { background: #f9f9f9; }
.price { color: #1B5E20; font-weight: bold; }
.red { color: #d32f2f; font-weight: bold; }
.note { background: #FFF3E0; padding: 12px; border-radius: 6px; font-size: 13px; line-height: 1.8; white-space: pre-wrap; }
.json-box { background: #263238; color: #A5D6A7; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 11px; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }
img.preview { max-width: 200px; max-height: 150px; margin: 5px; border-radius: 6px; border: 2px solid #ddd; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; color: #fff; font-weight: bold; font-size: 12px; }
.badge-진행 { background: #2196F3; }
.badge-유찰 { background: #FF9800; }
.badge-매각 { background: #9E9E9E; }
.badge-소멸 { background: #607D8B; }
.badge-인수 { background: #f44336; }
.badge-소멸기준 { background: #FF5722; }
.badge-green { background: #4CAF50; }
.count { display: inline-block; background: #E3F2FD; color: #1565C0; padding: 2px 8px; border-radius: 8px; font-size: 12px; font-weight: bold; margin-left: 5px; }
</style>
</head>
<body>
<h1>🔍 전체 파싱 결과 """ + case_number + """</h1>
"""

# 기본정보
html += '<div class="section"><h2>📋 기본정보</h2><table>'
for field in ['법원전체명', '경매계', '사건번호전체', '매각일시', '소재지', '물건종류', '경매종류', '경매대상',
              '채권자', '채무자', '소유자', '감정가', '최저가', '청구금액', '보증금', '토지면적', '건물면적', '관련사건']:
    val = result.get(field, '-')
    cls = 'price' if any(k in field for k in ['감정가', '최저가', '청구금액', '보증금']) else ''
    html += f'<tr><td class="label">{field}</td><td class="{cls}">{val}</td></tr>'
html += '</table></div>'

# 입찰이력
bids = result.get('입찰이력', [])
if bids:
    html += f'<div class="section"><h2>📊 입찰이력 <span class="count">{len(bids)}건</span></h2><table>'
    html += '<tr><th>회차</th><th>입찰기일</th><th>최저입찰금액</th><th>결과</th><th>낙찰가</th></tr>'
    for b in bids:
        result_text = b.get('결과', '')
        cls = f'badge badge-{result_text}' if result_text in ['진행', '유찰', '매각'] else ''
        html += f'<tr><td>{b.get("회차","")}</td><td>{b.get("입찰기일","")}</td><td class="price">{b.get("최저입찰금액","")}</td><td><span class="{cls}">{result_text}</span></td><td>{b.get("낙찰가","-")}</td></tr>'
    html += '</table></div>'

# 물건사진
photos = result.get('물건사진', [])
if photos:
    html += f'<div class="section"><h2>📷 물건사진 <span class="count">{len(photos)}장</span></h2>'
    for url in photos:
        html += f'<img class="preview" src="{url}" onerror="this.style.display=\'none\'">'
    html += '</div>'

# 감정평가목록
appraisal = result.get('감정평가목록', [])
if appraisal:
    html += f'<div class="section"><h2>🏚️ 감정평가현황 (목록) <span class="count">{len(appraisal)}건</span></h2><table>'
    html += '<tr><th>목록</th><th>주소</th><th>구조/용도/대지권</th><th>면적</th><th>비고</th></tr>'
    for a in appraisal:
        html += f'<tr><td>{a["목록"]}</td><td>{a["주소"]}</td><td>{a["구조용도대지권"]}</td><td>{a["면적"]}</td><td>{a["비고"]}</td></tr>'
    html += '</table></div>'

# 차량 감정평가
vehicle_fields = {k: v for k, v in result.items() if k.startswith('감정_')}
if vehicle_fields:
    html += '<div class="section"><h2>🚗 감정평가현황 (차량)</h2><table>'
    for k, v in vehicle_fields.items():
        html += f'<tr><td class="label">{k.replace("감정_","")}</td><td>{v}</td></tr>'
    html += '</table></div>'

# 요약
if result.get('요약'):
    html += '<div class="section"><h2>📝 요약 (감정평가)</h2><div class="note">' + result['요약'].replace('. ', '.<br>') + '</div></div>'

# 참고사항 (감정평가)
if result.get('참고사항_감정'):
    html += '<div class="section"><h2>⚠️ 참고사항 (감정평가)</h2><div class="note">' + result['참고사항_감정'] + '</div></div>'

# 임차인현황
tenants_data = result.get('임차인현황', [])
if tenants_data:
    html += '<div class="section"><h2>🏠 임차인현황</h2>'
    if result.get('배당요구종기'):
        html += f'<p style="color:#d32f2f;font-weight:bold;margin-bottom:10px;">{result["배당요구종기"]}</p>'
    
    # 테이블 형태인지 내용 형태인지 구분
    has_table = any(t.get('임차인') for t in tenants_data if '임차인' in t)
    if has_table:
        html += '<table><tr><th>임차인</th><th>용도/점유</th><th>전입일자</th><th>확정일자</th><th>배당요구일</th><th>보증금/월세</th><th>대항력</th></tr>'
        for t in tenants_data:
            if '내용' in t:
                html += f'<tr><td colspan="7" style="background:#f5f5f5;">{t["내용"]}</td></tr>'
            else:
                html += f'<tr><td>{t.get("임차인","")}</td><td>{t.get("용도점유","")}</td><td>{t.get("전입일자","")}</td><td>{t.get("확정일자","")}</td><td>{t.get("배당요구일","")}</td><td class="price">{t.get("보증금월세","")}</td><td>{t.get("대항력","")}</td></tr>'
        html += '</table>'
    else:
        for t in tenants_data:
            for k, v in t.items():
                html += f'<p><b>{k}:</b> {v}</p>'
    html += '</div>'

# 등기부현황
reg_data = result.get('등기부현황', [])
if reg_data:
    html += f'<div class="section"><h2>📄 건물 등기부현황 <span class="count">{len(reg_data)}건</span></h2><table>'
    html += '<tr><th>구분</th><th>성립일자</th><th>권리</th><th>권리자</th><th>권리금액</th><th>인수/소멸</th></tr>'
    for r in reg_data:
        sose = r.get('인수소멸', '')
        cls = ''
        if '소멸' in sose:
            cls = 'badge-소멸'
        elif '인수' in sose:
            cls = 'badge-인수'
        elif '기준' in sose:
            cls = 'badge-소멸기준'
        html += f'<tr><td>{r["구분"]}</td><td>{r["성립일자"]}</td><td>{r["권리"]}</td><td>{r["권리자"]}</td><td class="price">{r["권리금액"]}</td><td><span class="badge {cls}">{sose}</span></td></tr>'
    html += '</table></div>'

# 주의사항
html += '<div class="section"><h2>⚠️ 주의사항</h2><table>'
html += f'<tr><td class="label">소멸되지않는 등기부권리</td><td>{result.get("소멸되지않는등기부권리") or "해당사항없음"}</td></tr>'
html += f'<tr><td class="label">소멸되지않는 지상권</td><td>{result.get("소멸되지않는지상권") or "해당사항없음"}</td></tr>'
html += f'<tr><td class="label">주의사항</td><td>{result.get("주의사항") or "-"}</td></tr>'
html += '</table></div>'

# 인근매각통계
stats_data = result.get('인근매각통계', {})
if stats_data:
    html += '<div class="section"><h2>📈 인근매각통계</h2><table>'
    html += '<tr><th>사례기간</th><th>낙찰물건수</th><th>평균감정가</th><th>평균낙찰가</th><th>유찰횟수</th></tr>'
    for period in ['3개월', '6개월', '12개월']:
        s = stats_data.get(period, {})
        if s:
            html += f'<tr><td>{period}</td><td>{s.get("낙찰물건수","")}</td><td class="price">{s.get("평균감정가","")}</td><td class="price">{s.get("평균낙찰가","")}</td><td>{s.get("유찰횟수","")}</td></tr>'
    html += '</table></div>'

# RAW JSON
html += '<div class="section"><h2>🔖 전체 RAW 데이터</h2>'
html += f'<div class="json-box">{json.dumps(result, ensure_ascii=False, indent=2)}</div></div>'

html += '</body></html>'

outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'view_parse_test.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)

webbrowser.open(outpath)
print(f"\n✅ 결과: {outpath}")