"""
gfauction.co.kr 경매 물건 크롤러 v2
- Base64 로그인
- 검색 결과 리스트 파싱 (페이지네이션)
- 상세 페이지 파싱 (물건종류별 상세정보)
- 이미지 다운로드 (images/지역/물건종류/)
- SQLite DB 저장
"""
import requests
from bs4 import BeautifulSoup
import base64
import re
import sqlite3
import time
import os
import json
import random
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

# ======================================
# 설정 (config.py에서 로드)
# ======================================
from config import (
    BASE_URL, BASE_DIR, DB_PATH, IMAGE_BASE_DIR,
    LOGIN_ID, LOGIN_PW,
    DELAY_LIST, DELAY_DETAIL, DELAY_IMAGE,
    EXCLUDE_STATUS, EXCLUDE_ITEM_TYPE,
)
from db_setup import init_db, get_item_type_name, get_category, ITEM_TYPE_MAP

# ======================================
# 유틸리티
# ======================================
def parse_price(text):
    """가격 문자열을 정수로 변환 ('1,800,000' -> 1800000)"""
    if not text:
        return 0
    text = text.replace(',', '').replace('원', '').replace(' ', '').strip()
    # 숫자만 추출
    text = re.sub(r'[^0-9]', '', text)
    if not text:
        return 0
    try:
        val = int(text)
        # SQLite INTEGER 최대값 초과 방지
        return min(val, 9223372036854775807)
    except (ValueError, OverflowError):
        return 0

def clean_text(text):
    """텍스트 정리"""
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('\xa0', ' ')
    return text

def safe_filename(name):
    """파일명으로 사용 가능한 문자열로 변환"""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip()[:50]
    return name if name else 'unknown'

# ======================================
# 로그인
# ======================================
def login(session):
    """Base64 인코딩으로 로그인"""
    print("\n[로그인] 시도 중...")
    
    login_page_url = f'{BASE_URL}/member/member01.php'
    session.get(login_page_url, timeout=15)
    
    encoded_id = base64.b64encode(LOGIN_ID.encode('utf-8')).decode('utf-8')
    encoded_pw = base64.b64encode(LOGIN_PW.encode('utf-8')).decode('utf-8')
    
    resp = session.post(f'{BASE_URL}/member/login_proc.php', data={
        'rtn_page': '',
        'id': encoded_id,
        'pwd': encoded_pw,
        'login_id': '',
        'login_pw': '',
    }, timeout=15, headers={
        'Referer': login_page_url,
        'Origin': BASE_URL,
    })
    
    resp_check = session.get(f'{BASE_URL}/main/main.php', timeout=15)
    if '로그아웃' in resp_check.text:
        print("[로그인] ✅ 성공!")
        return True
    else:
        print("[로그인] ❌ 실패!")
        return False

# ======================================
# 검색 결과 리스트 파싱
# ======================================
def parse_list_page(session, page=1, rows=20, sno='', extra_params=None):
    """검색 결과 페이지에서 물건 목록 파싱"""
    list_url = f'{BASE_URL}/search/search_list.php'
    
    params = {
        'aresult': 'all',
        'rows': str(rows),
        'page': str(page),
    }
    if sno:
        params['sno'] = sno
    if extra_params:
        params.update(extra_params)
    
    resp = session.get(list_url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code}")
        return [], 0
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 총 건수 확인
    total_count = 0
    count_text = soup.find(string=re.compile(r'총\s*\d+건'))
    if count_text:
        m = re.search(r'(\d+)', str(count_text))
        if m:
            total_count = int(m.group(1))
    
    # 테이블에서 물건 추출
    items = []
    table = soup.find('table', class_='tbl_list')
    if not table:
        return [], total_count
    
    trs = table.find_all('tr')
    for tr in trs:
        if tr.find('th'):
            continue
        
        chk = tr.find('input', {'name': 'aChk'})
        if not chk:
            continue
        
        item = {}
        item['internal_id'] = chk.get('value', '')
        
        # 상세페이지 idx (onclick에서 추출)
        first_onclick_td = tr.find('td', onclick=True)
        if first_onclick_td:
            onclick_text = first_onclick_td.get('onclick', '')
            m = re.search(r"idx=(\d+)", onclick_text)
            if m:
                item['detail_idx'] = m.group(1)
        
        # 썸네일 이미지
        img = tr.find('img')
        if img and img.get('src'):
            item['thumbnail_url'] = img.get('src', '')
        
        # 모든 onclick td에서 전체 이미지 URL 추출
        img_srcs = []
        for img_tag in tr.find_all('img'):
            src = img_tag.get('src', '')
            if src and 'sample_img' not in src:
                img_srcs.append(src)
        if img_srcs:
            item['all_photo_urls'] = img_srcs
        
        # ul/li 구조에서 데이터 추출
        uls = tr.find_all('ul')
        ul_data = {}
        for ul in uls:
            cls = ' '.join(ul.get('class', []))
            lis = ul.find_all('li')
            for li in lis:
                li_cls = ' '.join(li.get('class', []))
                li_text = li.get_text(strip=True)
                
                if 'list_sell01' in cls:
                    if 'lest_test01' in li_cls:
                        ul_data['구분'] = li_text
                    elif 'lest_test02' in li_cls:
                        ul_data['물건종류_li'] = li_text  # 법원 or 물건종류
                    elif li_text and not li_cls:
                        if 'ul_sell01_date' not in ul_data:
                            ul_data['ul_sell01_date'] = li_text
                
                elif 'list_sell02' in cls:
                    if 'lest_test06' in li_cls:
                        ul_data['사건번호'] = li_text
                    elif 'lest_test05' in li_cls:
                        ul_data['소재지'] = li_text
                
                elif 'list_sell03' in cls:
                    if 'lest_test03' in li_cls:
                        ul_data['감정가'] = li_text
                    elif 'lest_test04' in li_cls:
                        ul_data['최저가'] = li_text
                    elif 'lest_test07' in li_cls:
                        ul_data['매각가'] = li_text
        
        # 두 번째 list_sell01 (상태 정보) - 별도 추출
        sell01_count = 0
        for ul in uls:
            cls = ' '.join(ul.get('class', []))
            if 'list_sell01' in cls:
                sell01_count += 1
                if sell01_count == 2:
                    lis2 = ul.find_all('li')
                    for li in lis2:
                        li_cls = ' '.join(li.get('class', []))
                        li_text = li.get_text(strip=True)
                        if 'lest_test03' in li_cls:
                            ul_data['상태'] = li_text
                        elif 'lest_test04' in li_cls:
                            ul_data['최저가비율'] = li_text
                        elif 'lest_test07' in li_cls:
                            ul_data['매각가비율'] = li_text
        
        # item에 매핑
        item['case_number'] = ul_data.get('사건번호', '')
        item['address'] = ul_data.get('소재지', '')
        item['appraisal_price'] = parse_price(ul_data.get('감정가', '0'))
        item['min_price'] = parse_price(ul_data.get('최저가', '0'))
        item['sale_price'] = parse_price(ul_data.get('매각가', '0'))
        item['status'] = ul_data.get('상태', '')
        item['min_rate'] = ul_data.get('최저가비율', '')
        item['sale_rate'] = ul_data.get('매각가비율', '')
        
        # 날짜, 법원, 물건종류 (첫 번째 list_sell01에서)
        sell01_count2 = 0
        for ul in uls:
            cls = ' '.join(ul.get('class', []))
            if 'list_sell01' in cls:
                sell01_count2 += 1
                if sell01_count2 == 1:
                    lis3 = ul.find_all('li')
                    texts3 = [li.get_text(strip=True) for li in lis3]
                    # 보통: [날짜, 구분, 법원, 물건종류]
                    if len(texts3) >= 1 and re.match(r'\d{4}\.\d{2}\.\d{2}', texts3[0]):
                        item['sale_date'] = texts3[0]
                    if len(texts3) >= 3:
                        item['court'] = texts3[2]
                    if len(texts3) >= 4:
                        item['item_type'] = texts3[3]
        
        # 조회수
        all_tds = tr.find_all('td')
        if all_tds:
            last_text = all_tds[-1].get_text(strip=True)
            if last_text.isdigit():
                item['views'] = int(last_text)
        
        items.append(item)
    
    return items, total_count

# ======================================
# 상세 페이지 파싱
# ======================================
def parse_detail_page(session, internal_id):
    """상세 페이지에서 추가 정보 파싱"""
    detail_url = f'{BASE_URL}/search/detail_view.php?idx={internal_id}'
    resp = session.get(detail_url, timeout=15)
    
    if resp.status_code != 200 or len(resp.text) < 1000:
        return None
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    detail = {'internal_id': internal_id, 'tenants': [], 'documents': []}
    
    # ---------------------------
    # 기본 메인 페이지 파싱
    # ---------------------------
    tables = soup.find_all('table', class_='tbl_dtb')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            ths = row.find_all('th')
            tds = row.find_all('td')
            
            if not ths and not tds: continue
            
            th_texts = [clean_text(th.get_text()) for th in ths]
            td_texts = [clean_text(td.get_text()) for td in tds]
            
            for i, th in enumerate(th_texts):
                td_val = td_texts[i] if i < len(td_texts) else ''
                if th == '소재지': detail['address'] = td_val.replace('대법원바로가기', '').strip()
                elif th == '물건종류': detail['item_type'] = td_val
                elif th == '채권자': detail['creditor'] = td_val
                elif th == '경매대상': detail['auction_target'] = td_val
                elif th == '채무자': detail['debtor'] = td_val
                elif th == '소유자': detail['owner'] = td_val
                elif th == '토지면적': detail['land_area'] = td_val
                elif th == '건물면적': detail['building_area'] = td_val
                elif th == '감정가': detail['appraisal_price'] = td_val
                elif th == '경매종류': detail['auction_type'] = td_val
                elif th == '최저가': detail['min_price_detail'] = td_val
                elif th == '청구금액': detail['claim_amount'] = td_val
                elif th == '보증금': detail['deposit'] = td_val
                elif th == '관련사건': detail['related_case'] = td_val.replace('이송전사건사건검색', '').replace('사건검색', '').strip()
            
            # 차량 정보 테이블
            if len(th_texts) == 3 and len(td_texts) == 3:
                for th, td in zip(th_texts, td_texts):
                    if th == '차 명': detail['vehicle_name'] = td
                    elif th == '연 식': detail['vehicle_year'] = td
                    elif th == '제조사': detail['vehicle_maker'] = td
                    elif th == '연 료': detail['vehicle_fuel'] = td
                    elif th == '변속기': detail['vehicle_transmission'] = td
                    elif th == '등록번호': detail['vehicle_reg_number'] = td
                    elif th == '원동기형식': detail['vehicle_engine_type'] = td
                    elif th == '주행거리': detail['vehicle_mileage'] = td
                    elif th == '배기량': detail['vehicle_displacement'] = td
                    elif th == '승인번호': detail['vehicle_approval_number'] = td
                    elif th == '차대번호': detail['vehicle_vin'] = td
            
            # 보관장소
            if th_texts and th_texts[0] == '보관장소':
                detail['vehicle_storage'] = td_texts[0] if td_texts else ''
    
    # 요약/참고사항
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            ths = row.find_all('th')
            th_text = clean_text(''.join(th.get_text() for th in ths))
            if '요약' in th_text:
                detail['appraisal_summary'] = clean_text(tds[-1].get_text()) if tds else ''
            elif '참고사항' in th_text:
                detail['notes'] = clean_text(tds[-1].get_text()) if tds else ''
    
    # 소멸되지 않는 권리, 주의사항, 임차인 현황 (테이블 헤더 패턴)
    for table in soup.find_all('table', class_='tbl_dtb'):
        rows = table.find_all('tr')
        if not rows: continue
        
        # 첫 번째 행의 헤더 텍스트들
        header_ths = [clean_text(th.get_text()) for th in rows[0].find_all('th')]
        
        # 임차인 테이블 파싱
        if len(header_ths) >= 7 and '임차인' in header_ths[0] and '용도/점유' in header_ths[1]:
            for row in rows[1:]:
                tds = [clean_text(td.get_text()) for td in row.find_all('td')]
                if len(tds) >= 7:
                    if '현황조사서기타' in tds[0]:
                        detail['status_survey_note'] = tds[1] if len(tds) > 1 else ''
                    elif '대항력' not in tds[0]: # 헤더가 아닌 실제 데이터
                        tenant = {
                            'tenant_name': tds[0],
                            'usage_occupancy': tds[1],
                            'move_in_date': tds[2],
                            'fixed_date': tds[3],
                            'dividend_request_date': tds[4],
                            'deposit_rent': tds[5],
                            'has_opposing_power': tds[6],
                            'note': tds[7] if len(tds) > 7 else ''
                        }
                        
                        # 보증금/월세 분리
                        deposit_str = tenant['deposit_rent'].replace('원', '').replace(',', '').strip()
                        if '월' in deposit_str:
                            parts = deposit_str.split('월')
                            dep_num = re.sub(r'[^0-9]', '', parts[0])
                            rent_num = re.sub(r'[^0-9]', '', parts[1]) if len(parts) > 1 else ''
                            tenant['deposit'] = min(int(dep_num), 9223372036854775807) if dep_num else 0
                            tenant['monthly_rent'] = min(int(rent_num), 9223372036854775807) if rent_num else 0
                        else:
                            dep_num = re.sub(r'[^0-9]', '', deposit_str)
                            tenant['deposit'] = min(int(dep_num), 9223372036854775807) if dep_num else 0
                            tenant['monthly_rent'] = 0
                            
                        detail['tenants'].append(tenant)

        # 소멸되지 않는 권리 등
        for row in rows:
            ths = [clean_text(th.get_text()) for th in row.find_all('th')]
            tds = [clean_text(td.get_text()) for td in row.find_all('td')]
            for th, td in zip(ths, tds):
                if '소멸되지 않는 등기부권리' in th:
                    detail['non_extinguishable_rights'] = td
                elif '소멸되지 않는 지상권' in th:
                    detail['non_extinguishable_easement'] = td
                elif '주의사항' in th:
                    if not detail.get('notes'):
                        detail['notes'] = td
    
    # 입찰 이력
    bid_history = []
    history_table = soup.find('table', class_='tbl_dtb_history')
    if history_table:
        for row in history_table.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) >= 4:
                bid = {
                    'bid_round': clean_text(tds[0].get_text()),
                    'bid_date': clean_text(tds[1].get_text()),
                    'min_bid_price': clean_text(tds[2].get_text()),
                    'result': clean_text(tds[3].get_text()),
                }
                bid_history.append(bid)
            elif len(tds) == 1:
                text = clean_text(tds[0].get_text())
                if bid_history:
                    bid_history[-1]['sale_info'] = text
    detail['bid_history'] = bid_history
    
    # 배당요구종기 파싱
    claim_match = re.search(r'\[배당요구종기\s*:\s*(.*?)\]', resp.text)
    if claim_match:
        detail['claim_deadline'] = clean_text(claim_match.group(1))
    
    # ---------------------------
    # judge_text / judDiv 파싱 (감정평가서 요약 + 전체 - 상세페이지 내장)
    # ---------------------------
    judge_text_div = soup.find('div', id='judge_text')
    if judge_text_div:
        # 요약: judDiv 앞쪽 텍스트 (script 제외)
        summary_parts = []
        for child in judge_text_div.children:
            if hasattr(child, 'name') and child.name:
                if child.name == 'script' or child.name == 'style':
                    continue
                if child.get('id') == 'judDiv':
                    break
                text = child.get_text(strip=True)
                if text:
                    summary_parts.append(text)
            else:
                text = str(child).strip()
                if text:
                    summary_parts.append(text)
        if summary_parts:
            detail['appraisal_summary'] = clean_text(' '.join(summary_parts))
        
        # 전체: judDiv 내용
        jud_div = judge_text_div.find('div', id='judDiv')
        if jud_div:
            report_html = str(jud_div)
            report_text = BeautifulSoup(report_html, 'html.parser').get_text(separator='\n').strip()
            report_text = re.sub(r'\n{3,}', '\n\n', report_text)
            detail['appraisal_report'] = report_text
            
            struct_match = re.search(r'([가-힣]+조)\s+([가-힣]+지붕)?\s*(\d+)층\s*건물\s*내\s*(\d+)층', report_text)
            if struct_match:
                detail['building_structure'] = struct_match.group(1)
                detail['building_roof'] = struct_match.group(2) if struct_match.group(2) else ''
                detail['total_floors'] = int(struct_match.group(3))
                detail['target_floor'] = int(struct_match.group(4))
            
            detail['heating_type'] = '개별난방' if '개별난방' in report_text else ('중앙난방' if '중앙난방' in report_text else '')
            detail['parking_available'] = 1 if '주차장' in report_text or '주차시설' in report_text else 0
            detail['elevator_available'] = 1 if '승강기' in report_text else 0
            
            land_match = re.search(r'8\)\s*토지이용계획.*?=(.*?)(?=\n\n|\n9\)|$)', report_text, re.DOTALL)
            if land_match:
                detail['land_use_plan'] = clean_text(land_match.group(1))

    # ---------------------------
    # 팝업 페이지 정보 수집 (올바른 URL: auction_detail_view.php)
    # ---------------------------
    popup_base = f'{BASE_URL}/search/auction_detail_view.php'
    detail['pdf_urls'] = []
    
    try:
        # 1. 감정평가서 - PDF URL 추출
        j_resp = session.get(f'{popup_base}?type=judgement&idx={internal_id}', timeout=10)
        if j_resp.status_code == 200 and len(j_resp.text) > 500:
            j_soup = BeautifulSoup(j_resp.text, 'html.parser')
            for a in j_soup.find_all('a', href=True):
                href = a.get('href', '')
                if '.pdf' in href.lower():
                    detail['pdf_urls'].append(href)
            for embed in j_soup.find_all(['embed', 'iframe']):
                src = embed.get('src', '')
                if src and '.pdf' in src.lower():
                    detail['pdf_urls'].append(src)
            if not detail.get('appraisal_report'):
                detail['appraisal_report'] = j_soup.get_text(separator='\n').strip()

        # 2. 현황조사서
        s_resp = session.get(f'{popup_base}?type=status&idx={internal_id}', timeout=10)
        if s_resp.status_code == 200 and len(s_resp.text) > 500:
            s_soup = BeautifulSoup(s_resp.text, 'html.parser')
            detail['status_report'] = s_soup.get_text(separator='\n').strip()
            
        # 3. 문건접수내역 (2컬럼: 접수일, 접수내역)
        m_resp = session.get(f'{popup_base}?type=mun&idx={internal_id}', timeout=10)
        if m_resp.status_code == 200 and len(m_resp.text) > 500:
            m_soup = BeautifulSoup(m_resp.text, 'html.parser')
            for table in m_soup.find_all('table'):
                for row in table.find_all('tr'):
                    tds = [clean_text(td.get_text()) for td in row.find_all('td')]
                    if len(tds) >= 2:
                        if '접수일' in tds[0] or '접수내역' in tds[0]:
                            continue
                        if tds[0] and tds[1]:
                            detail['documents'].append({
                                'doc_date': tds[0],
                                'doc_type': '',
                                'doc_description': tds[1]
                            })

        # 4. 매각물건명세서
        mul_resp = session.get(f'{popup_base}?type=mul&idx={internal_id}', timeout=10)
        if mul_resp.status_code == 200 and len(mul_resp.text) > 500:
            mul_soup = BeautifulSoup(mul_resp.text, 'html.parser')
            detail['sale_statement'] = mul_soup.get_text(separator='\n').strip()
            
        # 5. 부동산의표시
        bu_resp = session.get(f'{popup_base}?type=bu&idx={internal_id}', timeout=10)
        if bu_resp.status_code == 200 and len(bu_resp.text) > 500:
            bu_soup = BeautifulSoup(bu_resp.text, 'html.parser')
            detail['property_list'] = bu_soup.get_text(separator='\n').strip()
            
        # 6. 송달내역
        song_resp = session.get(f'{popup_base}?type=song&idx={internal_id}', timeout=10)
        if song_resp.status_code == 200 and len(song_resp.text) > 500:
            song_soup = BeautifulSoup(song_resp.text, 'html.parser')
            detail['delivery_records'] = song_soup.get_text(separator='\n').strip()

    except Exception as e:
        print(f"팝업 파싱 에러 (id={internal_id}): {e}")

    # 이미지 URL
    photo_urls = []
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'pic_courtauction' in src or 'nuriauction' in src:
            if 'thumb' not in src and 'sample_img' not in src:
                photo_urls.append(src)
    detail['photo_urls'] = photo_urls
    
    return detail

# ======================================
# 이미지 다운로드
# ======================================
def download_images(session, internal_id, item_data, force=False):
    """이미지를 D:\gfauction_images\지역\물건종류\ 에 다운로드"""
    court = safe_filename(item_data.get('court', '미확인'))
    item_type = safe_filename(item_data.get('item_type', '기타'))
    case_number = safe_filename(item_data.get('case_number', str(internal_id)))
    
    # 폴더 구조: D:\gfauction_images\법원\물건종류\사건번호\
    save_dir = os.path.join(IMAGE_BASE_DIR, court, item_type, case_number)
    os.makedirs(save_dir, exist_ok=True)
    
    downloaded_paths = []
    
    # 썸네일 URL에서 원본 이미지 URL 추출
    urls = []
    thumbnail_url = item_data.get('thumbnail_url', '')
    if thumbnail_url and 'sample_img' not in thumbnail_url:
        urls.append(thumbnail_url)
    
    # 상세에서 추출한 이미지 URL
    photo_urls = item_data.get('photo_urls', [])
    if isinstance(photo_urls, str):
        try:
            photo_urls = json.loads(photo_urls)
        except:
            photo_urls = []
    urls.extend(photo_urls)
    
    # 중복 제거
    urls = list(dict.fromkeys(urls))
    
    for idx, url in enumerate(urls):
        try:
            # 파일 확장자 결정
            if '.jpg' in url.lower():
                ext = '.jpg'
            elif '.png' in url.lower():
                ext = '.png'
            elif '.gif' in url.lower():
                ext = '.gif'
            else:
                ext = '.jpg'
            
            filename = f"{internal_id}_{idx+1}{ext}"
            filepath = os.path.join(save_dir, filename)
            
            if os.path.exists(filepath) and not force:
                downloaded_paths.append(filepath)
                continue
            
            resp = session.get(url, timeout=15, stream=True)
            if resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                downloaded_paths.append(filepath)
                time.sleep(DELAY_IMAGE)
            else:
                print(f"    이미지 다운로드 실패: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    이미지 오류: {e}")
    
    return downloaded_paths

# ======================================
# DB 저장
# ======================================
def save_items_to_db(items):
    """리스트 아이템들을 DB에 저장 (기존 상세데이터 보존)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0
    
    for item in items:
        try:
            internal_id = int(item.get('internal_id', 0))
            if not internal_id:
                continue
            
            # 사건번호 파싱 (예: 2026-10086)
            case_number = item.get('case_number', '')
            case_parts = case_number.split('-') if '-' in case_number else ['', '']
            case_year = case_parts[0] if len(case_parts) >= 1 else ''
            case_seq = case_parts[1] if len(case_parts) >= 2 else ''
            
            # 물건종류 코드 찾기
            item_type = item.get('item_type', '')
            item_type_code = ''
            for code, name in ITEM_TYPE_MAP.items():
                if name == item_type:
                    item_type_code = code
                    break
            category = get_category(item_type_code) if item_type_code else ''
            
            # 주소에서 시도 추출
            address = item.get('address', '')
            address_sido = ''
            sido_list = ['서울', '경기', '인천', '강원', '충남', '충북', '대전', '세종',
                        '부산', '울산', '대구', '경북', '경남', '전남', '광주', '전북', '제주']
            for sido in sido_list:
                if sido in address:
                    address_sido = sido
                    break
            
            # INSERT OR REPLACE 대신 INSERT + UPDATE 사용 (detail_scraped 등 기존 데이터 보존)
            cursor.execute('''
                INSERT INTO auction_items (
                    internal_id, case_number, case_year, case_seq,
                    court, item_type_code, item_type, category,
                    address, address_sido,
                    appraisal_price, min_price, sale_price,
                    min_rate, sale_rate,
                    sale_date, status, views,
                    thumbnail_url,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+9 hours'))
                ON CONFLICT(internal_id) DO UPDATE SET
                    case_number = excluded.case_number,
                    case_year = excluded.case_year,
                    case_seq = excluded.case_seq,
                    court = excluded.court,
                    item_type_code = COALESCE(NULLIF(excluded.item_type_code, ''), auction_items.item_type_code),
                    item_type = COALESCE(NULLIF(excluded.item_type, ''), auction_items.item_type),
                    category = COALESCE(NULLIF(excluded.category, ''), auction_items.category),
                    address = excluded.address,
                    address_sido = excluded.address_sido,
                    appraisal_price = excluded.appraisal_price,
                    min_price = excluded.min_price,
                    sale_price = excluded.sale_price,
                    min_rate = excluded.min_rate,
                    sale_rate = excluded.sale_rate,
                    sale_date = excluded.sale_date,
                    status = excluded.status,
                    views = excluded.views,
                    thumbnail_url = COALESCE(NULLIF(excluded.thumbnail_url, ''), auction_items.thumbnail_url),
                    updated_at = excluded.updated_at
            ''', (
                internal_id,
                case_number,
                case_year,
                case_seq,
                item.get('court', ''),
                item_type_code,
                item_type,
                category,
                address,
                address_sido,
                item.get('appraisal_price', 0),
                item.get('min_price', 0),
                item.get('sale_price', 0),
                item.get('min_rate', ''),
                item.get('sale_rate', ''),
                item.get('sale_date', ''),
                item.get('status', ''),
                item.get('views', 0),
                item.get('thumbnail_url', ''),
            ))
            saved += 1
        except Exception as e:
            print(f"  DB 저장 오류 ({item.get('internal_id', '?')}): {e}")
    
    conn.commit()
    conn.close()
    return saved

def save_detail_to_db(detail):
    """상세 정보를 DB에 업데이트"""
    if not detail:
        return False
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    try:
        raw_id = detail.get('internal_id', 0)
        internal_id = int(raw_id) if raw_id else 0
        if not internal_id:
            conn.close()
            return False
        
        # 물건종류 코드 업데이트
        item_type = detail.get('item_type', '')
        item_type_code = ''
        for code, name in ITEM_TYPE_MAP.items():
            if name == item_type:
                item_type_code = code
                break
        category = get_category(item_type_code) if item_type_code else ''
        
        # 통계 JSON
        stats = detail.get('stats', {})
        stats_3m = json.dumps(stats.get('3개월', {}), ensure_ascii=False) if '3개월' in stats else ''
        stats_6m = json.dumps(stats.get('6개월', {}), ensure_ascii=False) if '6개월' in stats else ''
        stats_12m = json.dumps(stats.get('12개월', {}), ensure_ascii=False) if '12개월' in stats else ''
        
        # photo_urls JSON
        photo_urls = detail.get('photo_urls', [])
        photo_urls_json = json.dumps(photo_urls, ensure_ascii=False) if photo_urls else ''
        
        cursor.execute('''
            UPDATE auction_items SET
                item_type_code = COALESCE(NULLIF(?, ''), item_type_code),
                item_type = COALESCE(NULLIF(?, ''), item_type),
                category = COALESCE(NULLIF(?, ''), category),
                address = COALESCE(NULLIF(?, ''), address),
                auction_type = ?,
                creditor = ?,
                debtor = ?,
                owner = ?,
                claim_amount = ?,
                deposit = ?,
                land_area = ?,
                building_area = ?,
                summary = ?,
                notes = ?,
                related_case = ?,
                tenant_info = ?,
                non_extinguishable_rights = ?,
                non_extinguishable_easement = ?,
                vehicle_name = ?,
                vehicle_year = ?,
                vehicle_maker = ?,
                vehicle_fuel = ?,
                vehicle_transmission = ?,
                vehicle_reg_number = ?,
                vehicle_engine_type = ?,
                vehicle_mileage = ?,
                vehicle_displacement = ?,
                vehicle_approval_number = ?,
                vehicle_vin = ?,
                vehicle_storage = ?,
                stats_3m = ?,
                stats_6m = ?,
                stats_12m = ?,
                photo_urls = ?,
                fail_count = ?,
                building_structure = COALESCE(NULLIF(?, ''), building_structure),
                building_roof = COALESCE(NULLIF(?, ''), building_roof),
                total_floors = CASE WHEN ? > 0 THEN ? ELSE total_floors END,
                target_floor = CASE WHEN ? > 0 THEN ? ELSE target_floor END,
                heating_type = COALESCE(NULLIF(?, ''), heating_type),
                parking_available = CASE WHEN ? = 1 THEN 1 ELSE parking_available END,
                elevator_available = CASE WHEN ? = 1 THEN 1 ELSE elevator_available END,
                land_use_plan = COALESCE(NULLIF(?, ''), land_use_plan),
                appraisal_summary = COALESCE(NULLIF(?, ''), appraisal_summary),
                appraisal_report = COALESCE(NULLIF(?, ''), appraisal_report),
                status_report = COALESCE(NULLIF(?, ''), status_report),
                claim_deadline = COALESCE(NULLIF(?, ''), claim_deadline),
                pdf_urls = COALESCE(NULLIF(?, ''), pdf_urls),
                sale_statement = COALESCE(NULLIF(?, ''), sale_statement),
                property_list = COALESCE(NULLIF(?, ''), property_list),
                delivery_records = COALESCE(NULLIF(?, ''), delivery_records),
                detail_scraped = 1,
                updated_at = datetime('now', '+9 hours')
            WHERE internal_id = ?
        ''', (
            item_type_code, item_type, category,
            detail.get('address', ''),
            detail.get('auction_type', ''),
            detail.get('creditor', ''),
            detail.get('debtor', ''),
            detail.get('owner', ''),
            parse_price(detail.get('claim_amount', '0')),
            parse_price(detail.get('deposit', '0')),
            detail.get('land_area', ''),
            detail.get('building_area', ''),
            detail.get('summary', ''),
            detail.get('notes', ''),
            detail.get('related_case', ''),
            detail.get('tenant_info', ''),
            detail.get('non_extinguishable_rights', ''),
            detail.get('non_extinguishable_easement', ''),
            detail.get('vehicle_name', ''),
            detail.get('vehicle_year', ''),
            detail.get('vehicle_maker', ''),
            detail.get('vehicle_fuel', ''),
            detail.get('vehicle_transmission', ''),
            detail.get('vehicle_reg_number', ''),
            detail.get('vehicle_engine_type', ''),
            detail.get('vehicle_mileage', ''),
            detail.get('vehicle_displacement', ''),
            detail.get('vehicle_approval_number', ''),
            detail.get('vehicle_vin', ''),
            detail.get('vehicle_storage', ''),
            stats_3m, stats_6m, stats_12m,
            photo_urls_json,
            detail.get('fail_count', 0),
            detail.get('building_structure', ''),
            detail.get('building_roof', ''),
            detail.get('total_floors', 0) or 0,
            detail.get('total_floors', 0) or 0,
            detail.get('target_floor', 0) or 0,
            detail.get('target_floor', 0) or 0,
            detail.get('heating_type', ''),
            detail.get('parking_available', 0),
            detail.get('elevator_available', 0),
            detail.get('land_use_plan', ''),
            detail.get('appraisal_summary', ''),
            detail.get('appraisal_report', ''),
            detail.get('status_report', ''),
            detail.get('claim_deadline', ''),
            json.dumps(detail.get('pdf_urls', []), ensure_ascii=False) if detail.get('pdf_urls') else '',
            detail.get('sale_statement', ''),
            detail.get('property_list', ''),
            detail.get('delivery_records', ''),
            internal_id,
        ))
        
        # 입찰 이력 저장
        bid_history = detail.get('bid_history', [])
        if bid_history:
            cursor.execute('DELETE FROM auction_bid_history WHERE internal_id = ?', (internal_id,))
            for bid in bid_history:
                cursor.execute('''
                    INSERT INTO auction_bid_history (internal_id, bid_round, bid_date, min_bid_price, result, sale_rate)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    internal_id,
                    bid.get('bid_round', ''),
                    bid.get('bid_date', ''),
                    parse_price(bid.get('min_bid_price', '0')),
                    bid.get('result', ''),
                    bid.get('sale_info', ''),
                ))
        
        # 임차인 정보 저장
        tenants = detail.get('tenants', [])
        if tenants:
            cursor.execute('DELETE FROM auction_tenants WHERE internal_id = ?', (internal_id,))
            for tenant in tenants:
                cursor.execute('''
                    INSERT INTO auction_tenants
                    (internal_id, tenant_name, usage_occupancy, move_in_date, fixed_date,
                     dividend_request_date, deposit, monthly_rent, has_opposing_power, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    internal_id, tenant.get('tenant_name'), tenant.get('usage_occupancy'),
                    tenant.get('move_in_date'), tenant.get('fixed_date'),
                    tenant.get('dividend_request_date'), tenant.get('deposit'),
                    tenant.get('monthly_rent'), tenant.get('has_opposing_power'), tenant.get('note')
                ))
        
        # 문건접수내역 저장
        documents = detail.get('documents', [])
        if documents:
            cursor.execute('DELETE FROM auction_documents WHERE internal_id = ?', (internal_id,))
            for doc in documents:
                cursor.execute('''
                    INSERT INTO auction_documents
                    (internal_id, doc_date, doc_type, doc_description)
                    VALUES (?, ?, ?, ?)
                ''', (
                    internal_id, doc.get('doc_date'), doc.get('doc_type'), doc.get('doc_description')
                ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  상세 DB 오류: {e}")
        conn.close()
        return False

def save_image_to_db(internal_id, image_url, local_path, order=0):
    """이미지 정보를 DB에 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO auction_images (internal_id, image_url, image_order, local_path, downloaded)
        VALUES (?, ?, ?, ?, 1)
    ''', (internal_id, image_url, order, local_path))
    conn.commit()
    conn.close()

# ======================================
# 메인 크롤링
# ======================================
def crawl_list_pages_worker(worker_id, start_page, end_page, sno=''):
    """개별 워커: start_page ~ end_page 까지 크롤링하며 매 페이지마다 DB 저장"""
    # 각 스레드마다 독립 세션 & 로그인
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    if not login(session):
        print(f"  [W{worker_id}] 로그인 실패. 종료.")
        return 0
    
    total_saved = 0
    for page in range(start_page, end_page + 1):
        items, total = parse_list_page(session, page=page, rows=50, sno=sno)
        if not items:
            print(f"  [W{worker_id}] 페이지 {page}: 데이터 없음. 종료.")
            break
        
        saved = save_items_to_db(items)
        total_saved += saved
        print(f"  [W{worker_id}] 페이지 {page}: {len(items)}건 → DB 저장 {saved}건 (누적 {total_saved})")
        time.sleep(DELAY_LIST)
    
    return total_saved


def crawl_list_pages(session, max_pages=0, sno='', num_workers=2):
    """리스트 페이지 크롤링 - 2개 스레드 병렬, 매 페이지마다 DB 저장"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    print(f"\n[리스트 크롤링] {num_workers}개 스레드 병렬 시작...")
    
    # 먼저 첫 페이지로 전체 페이지 수 파악
    items, total = parse_list_page(session, page=1, rows=50, sno=sno)
    if items:
        save_items_to_db(items)
        print(f"  첫 페이지: {len(items)}건 저장 (total={total})")
    
    # 전체 페이지 수 추정
    if total > 0:
        import math
        total_pages = math.ceil(total / 50)
    else:
        total_pages = 700  # fallback: 충분히 큰 수
        print(f"  total 건수를 알 수 없어 {total_pages}페이지까지 시도")
    
    print(f"  전체 약 {total_pages}페이지 → {num_workers}개 워커로 분할")
    
    # 페이지 범위를 워커 수만큼 분할 (page 2부터, page 1은 이미 처리)
    pages_per_worker = (total_pages - 1) // num_workers
    ranges = []
    for i in range(num_workers):
        sp = 2 + i * pages_per_worker
        ep = 2 + (i + 1) * pages_per_worker - 1 if i < num_workers - 1 else total_pages
        ranges.append((sp, ep))
    
    # 병렬 실행
    total_saved = len(items)  # 첫 페이지 분
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        for wid, (sp, ep) in enumerate(ranges):
            f = executor.submit(crawl_list_pages_worker, wid + 1, sp, ep, sno)
            futures[f] = wid + 1
        
        for f in as_completed(futures):
            wid = futures[f]
            try:
                saved = f.result()
                total_saved += saved
                print(f"  [W{wid}] 완료: {saved}건 저장")
            except Exception as e:
                print(f"  [W{wid}] 오류: {e}")
    
    print(f"  ✅ 전체 DB 저장 완료: 약 {total_saved}건")
    return total_saved

def crawl_detail_worker(worker_id, id_list):
    """개별 워커: 상세 페이지 크롤링 (5병렬) - 재로그인+재시도 내장"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    if not login(session):
        print(f"  [DW{worker_id}] 로그인 실패. 종료.")
        return 0
    
    success = 0
    fail = 0
    total = len(id_list)
    consecutive_fails = 0
    MAX_CONSECUTIVE_FAILS = 5
    
    for idx, internal_id in enumerate(id_list):
        try:
            detail = parse_detail_page(session, internal_id)
            if detail:
                # fail_count 계산 (입찰이력에서 유찰 횟수)
                bid_history = detail.get('bid_history', [])
                fail_count = 0
                for bid in bid_history:
                    result = bid.get('result', '')
                    if '유찰' in result:
                        fail_count += 1
                detail['fail_count'] = fail_count
                
                save_detail_to_db(detail)
                success += 1
                consecutive_fails = 0
            else:
                fail += 1
                consecutive_fails += 1
            
            # 연속 실패 시 재로그인
            if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                print(f"  [DW{worker_id}] 연속 {consecutive_fails}건 실패 → 재로그인...")
                time.sleep(5)
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                })
                if login(session):
                    # 재시도: 마지막 실패 건들 다시 시도
                    consecutive_fails = 0
                else:
                    print(f"  [DW{worker_id}] 재로그인 실패. 30초 대기 후 재시도...")
                    time.sleep(30)
                    if not login(session):
                        print(f"  [DW{worker_id}] 재로그인 최종 실패. 종료.")
                        break
                    consecutive_fails = 0
            
            if (idx + 1) % 50 == 0:
                print(f"  [DW{worker_id}] {idx+1}/{total} 진행중 (성공:{success}, 실패:{fail})")
            
            time.sleep(DELAY_DETAIL)
        except Exception as e:
            fail += 1
            consecutive_fails += 1
            print(f"  [DW{worker_id}] 오류 ID:{internal_id} - {e}")
            
            if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                print(f"  [DW{worker_id}] 연속 오류 → 재로그인...")
                time.sleep(5)
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                })
                login(session)
                consecutive_fails = 0
    
    print(f"  [DW{worker_id}] 완료: 성공 {success}, 실패 {fail}")
    return success


def crawl_details_parallel(num_workers=5):
    """DB에서 detail_scraped=0인 건을 5병렬로 상세 크롤링"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT internal_id FROM auction_items WHERE detail_scraped = 0 OR detail_scraped IS NULL")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not ids:
        print("  상세 크롤링 할 건이 없습니다.")
        return
    
    print(f"\n[상세 크롤링] {len(ids)}건, {num_workers}개 워커 병렬 시작...")
    print(f"  예상 소요: ~{len(ids) * DELAY_DETAIL / num_workers / 60:.0f}분")
    
    # ID 리스트를 워커 수만큼 분할
    chunk_size = len(ids) // num_workers + 1
    chunks = [ids[i:i+chunk_size] for i in range(0, len(ids), chunk_size)]
    
    total_success = 0
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        for wid, chunk in enumerate(chunks):
            f = executor.submit(crawl_detail_worker, wid + 1, chunk)
            futures[f] = wid + 1
        
        for f in as_completed(futures):
            wid = futures[f]
            try:
                success = f.result()
                total_success += success
            except Exception as e:
                print(f"  [DW{wid}] 오류: {e}")
    
    print(f"  ✅ 상세 크롤링 완료: 총 {total_success}건 성공")


def crawl_details(session, items, limit=0):
    """상세 페이지 크롤링 + 이미지 다운로드 (순차처리)"""
    print(f"\n[상세 크롤링] 시작 ({len(items)}건)...")
    
    count = 0
    for item in items:
        internal_id = item.get('internal_id')
        if not internal_id:
            continue
        
        count += 1
        
        case_number = item.get('case_number', '?')
        print(f"  [{count}/{len(items)}] {case_number} (ID:{internal_id}) 상세 수집 중...")
        
        detail = parse_detail_page(session, internal_id)
        if detail:
            save_detail_to_db(detail)
            merged = {**item, **detail}
            
            try:
                paths = download_images(session, internal_id, merged)
                if paths:
                    print(f"    📷 이미지 {len(paths)}장 다운로드")
                    for i, path in enumerate(paths):
                        save_image_to_db(internal_id, '', path, i)
            except Exception as e:
                print(f"    이미지 오류: {e}")
            
            print(f"    ✅ 상세 저장 완료")
        else:
            print(f"    ❌ 상세 페이지 없음")
        
        time.sleep(DELAY_DETAIL)
    
    print(f"  ✅ 상세 크롤링 완료: {count}건")

# ======================================
# 메인
# ======================================
def main():
    print("=" * 60)
    print("gfauction.co.kr 경매 크롤러 v2")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 0. DB 초기화
    print("\n[DB] 초기화...")
    init_db()
    
    # 1. 이미지 폴더 생성
    os.makedirs(IMAGE_BASE_DIR, exist_ok=True)
    print(f"[이미지] 저장 경로: {IMAGE_BASE_DIR}")
    
    # 2. 세션 생성 & 로그인
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    if not login(session):
        print("로그인 실패. 종료.")
        return
    
    # 3. 리스트 크롤링 (전체 연도, 페이지 무제한)
    items = crawl_list_pages(session, max_pages=0, sno='')
    
    # 4. 상세 크롤링 (5병렬)
    crawl_details_parallel(num_workers=5)
    
    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("크롤링 완료!")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM auction_items')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM auction_items WHERE detail_scraped = 1')
    detailed = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM auction_images WHERE downloaded = 1')
    images = cursor.fetchone()[0]
    
    cursor.execute('SELECT category, COUNT(*) FROM auction_items GROUP BY category ORDER BY COUNT(*) DESC')
    by_cat = cursor.fetchall()
    
    cursor.execute('SELECT status, COUNT(*) FROM auction_items GROUP BY status ORDER BY COUNT(*) DESC')
    by_status = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 수집 결과:")
    print(f"  총 물건: {total}건")
    print(f"  상세 수집: {detailed}건")
    print(f"  이미지: {images}장")
    print(f"\n  카테고리별:")
    for cat, cnt in by_cat:
        print(f"    {cat or '미분류'}: {cnt}건")
    print(f"\n  상태별:")
    for status, cnt in by_status:
        print(f"    {status or '미확인'}: {cnt}건")
    
    print(f"\n종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    import sys
    if '--detail-only' in sys.argv:
        # 리스트 스킵, 상세만 실행
        print("=" * 60)
        print("gfauction.co.kr 경매 크롤러 v2 (상세만)")
        print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        init_db()
        crawl_details_parallel(num_workers=4)
        print(f"\n종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        main()
