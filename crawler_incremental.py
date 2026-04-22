"""
gfauction.co.kr 증분 크롤러 (Incremental Crawler)
- 1단계: 리스트 빠른 스캔 (최근 10페이지 → 신규/변경 감지)
- 2단계: 변경 건만 상세 수집
- 변경 이력 추적 (item_changes 테이블)
- 크롤링 로그 기록 (crawl_log 테이블)

사용법:
  python crawler_incremental.py              # 증분 크롤링 (기본)
  python crawler_incremental.py --pages 20   # 스캔 페이지 수 지정
  python crawler_incremental.py --full-detail # 상태변경 건도 전체 상세 재수집
"""
import requests
from bs4 import BeautifulSoup
import base64
import sqlite3
import json
import time
import os
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 설정 (config.py에서 로드)
from config import (
    BASE_DIR, DB_PATH, LOG_DIR, IMAGE_BASE_DIR,
    BASE_URL, LOGIN_ID, LOGIN_PW,
    DELAY_LIST_INCREMENTAL, DELAY_DETAIL_INCREMENTAL, NUM_DETAIL_WORKERS,
)
from crawler import (
    login, parse_list_page, parse_detail_page,
    parse_price, clean_text, save_image_to_db
)
from db_setup import init_db, get_item_type_name, get_category, ITEM_TYPE_MAP

# 증분 크롤러용 딜레이
DELAY_LIST = DELAY_LIST_INCREMENTAL
DELAY_DETAIL = DELAY_DETAIL_INCREMENTAL

# ======================================
# 변경 감지 유틸리티
# ======================================
# 리스트에서 비교할 변경 감지 필드
LIST_COMPARE_FIELDS = ['status', 'min_price', 'appraisal_price', 'sale_price', 'sale_date', 'min_rate', 'sale_rate']

def get_db_item(conn, internal_id):
    """DB에서 기존 아이템 데이터 조회"""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM auction_items WHERE internal_id = ?', (internal_id,))
    row = cursor.fetchone()
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None

def detect_changes(old_item, new_item):
    """기존 데이터와 새 데이터 간 변경 사항 감지"""
    changes = []
    
    # 리스트 필드 비교
    field_map = {
        'status': '상태',
        'min_price': '최저가',
        'appraisal_price': '감정가',
        'sale_price': '매각가',
        'sale_date': '매각일',
        'min_rate': '최저가율',
        'sale_rate': '매각가율',
    }
    
    for field, label in field_map.items():
        old_val = str(old_item.get(field, '') or '')
        new_val = str(new_item.get(field, '') or '')
        if old_val != new_val and new_val:
            changes.append({
                'field': field,
                'label': label,
                'old': old_val,
                'new': new_val,
            })
    
    return changes

def log_changes(conn, internal_id, changes):
    """변경 이력을 item_changes 테이블에 기록"""
    cursor = conn.cursor()
    for change in changes:
        cursor.execute('''
            INSERT INTO item_changes (internal_id, change_type, old_value, new_value)
            VALUES (?, ?, ?, ?)
        ''', (internal_id, change['field'], change['old'], change['new']))
    conn.commit()

def save_item_to_db(conn, item):
    """개별 아이템을 DB에 저장 (INSERT OR REPLACE)"""
    cursor = conn.cursor()
    case_number = item.get('case_number', '')
    case_parts = case_number.split('-') if '-' in case_number else ['', '']
    case_year = case_parts[0] if len(case_parts) >= 1 else ''
    case_seq = case_parts[1] if len(case_parts) >= 2 else ''
    
    item_type = item.get('item_type', '')
    item_type_code = ''
    for code, name in ITEM_TYPE_MAP.items():
        if name == item_type:
            item_type_code = code
            break
    category = get_category(item_type_code) if item_type_code else ''
    
    address = item.get('address', '')
    address_sido = ''
    sido_list = ['서울', '경기', '인천', '강원', '충남', '충북', '대전', '세종',
                '부산', '울산', '대구', '경북', '경남', '전남', '광주', '전북', '제주']
    for sido in sido_list:
        if sido in address:
            address_sido = sido
            break
    
    # INSERT OR IGNORE: 기존 데이터 덮어쓰기 방지
    cursor.execute('''
        INSERT OR IGNORE INTO auction_items (
            internal_id, case_number, case_year, case_seq,
            court, item_type_code, item_type, category,
            address, address_sido,
            appraisal_price, min_price, sale_price,
            min_rate, sale_rate,
            sale_date, status, views,
            thumbnail_url,
            detail_scraped, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+9 hours'))
    ''', (
        int(item.get('internal_id', 0)),
        case_number, case_year, case_seq,
        item.get('court', ''), item_type_code, item_type, category,
        address, address_sido,
        item.get('appraisal_price', 0), item.get('min_price', 0), item.get('sale_price', 0),
        item.get('min_rate', ''), item.get('sale_rate', ''),
        item.get('sale_date', ''), item.get('status', ''), item.get('views', 0),
        item.get('thumbnail_url', ''),
        0,  # 신규 건은 detail_scraped = 0
    ))
    conn.commit()

def update_list_item(conn, item):
    """기존 아이템의 리스트 정보 업데이트 (변경 있을 때만)"""
    cursor = conn.cursor()
    internal_id = int(item.get('internal_id', 0))
    old = get_db_item(conn, internal_id)
    
    if not old:
        return False
    
    changes = detect_changes(old, item)
    if not changes:
        return False
    
    # 변경 이력 기록
    log_changes(conn, internal_id, changes)
    
    # 업데이트
    cursor.execute('''
        UPDATE auction_items SET
            status = ?,
            min_price = ?,
            appraisal_price = ?,
            sale_price = ?,
            min_rate = ?,
            sale_rate = ?,
            sale_date = ?,
            views = ?,
            updated_at = datetime('now', '+9 hours')
        WHERE internal_id = ?
    ''', (
        item.get('status', old.get('status', '')),
        item.get('min_price', old.get('min_price', 0)),
        item.get('appraisal_price', old.get('appraisal_price', 0)),
        item.get('sale_price', old.get('sale_price', 0)),
        item.get('min_rate', old.get('min_rate', '')),
        item.get('sale_rate', old.get('sale_rate', '')),
        item.get('sale_date', old.get('sale_date', '')),
        item.get('views', old.get('views', 0)),
        internal_id,
    ))
    conn.commit()
    return True

# ======================================
# 1단계: 리스트 빠른 스캔
# ======================================
def scan_list_pages(session, max_pages=10, sno=''):
    """최근 페이지만 스캔하여 신규/변경 건 감지"""
    print(f"\n{'='*60}")
    print(f"[1단계] 리스트 빠른 스캔 (최근 {max_pages}페이지)")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(DB_PATH)
    
    new_items = []      # 완전 신규
    changed_items = []   # 기존 건 중 변경
    total_scanned = 0
    
    for page in range(1, max_pages + 1):
        items, total = parse_list_page(session, page=page, rows=50, sno=sno)
        if not items:
            print(f"  페이지 {page}: 데이터 없음. 스캔 종료.")
            break
        
        for item in items:
            total_scanned += 1
            internal_id = int(item.get('internal_id', 0))
            old = get_db_item(conn, internal_id)
            
            if not old:
                # 신규 물건
                new_items.append(item)
            else:
                # 기존 물건 - 변경 감지
                changes = detect_changes(old, item)
                if changes:
                    changed_items.append((item, changes))
        
        print(f"  페이지 {page}: {len(items)}건 스캔 (신규:{len(new_items)}, 변경:{len(changed_items)})")
        time.sleep(DELAY_LIST)
    
    conn.close()
    
    print(f"\n  📊 스캔 결과:")
    print(f"     총 스캔: {total_scanned}건")
    print(f"     🆕 신규: {len(new_items)}건")
    print(f"     🔄 변경: {len(changed_items)}건")
    
    return new_items, changed_items, total_scanned

# ======================================
# 1단계 후처리: DB 저장 + 변경 로깅
# ======================================
def process_list_results(new_items, changed_items):
    """리스트 스캔 결과를 DB에 반영"""
    conn = sqlite3.connect(DB_PATH)
    
    # 신규 건 INSERT
    for item in new_items:
        save_item_to_db(conn, item)
    print(f"  ✅ 신규 {len(new_items)}건 DB 저장")
    
    # 변경 건 UPDATE + 로깅
    change_summary = {}
    for item, changes in changed_items:
        update_list_item(conn, item)
        for c in changes:
            label = c['label']
            change_summary[label] = change_summary.get(label, 0) + 1
    
    if change_summary:
        print(f"  ✅ 변경 {len(changed_items)}건 업데이트:")
        for label, count in change_summary.items():
            print(f"     - {label} 변경: {count}건")
    
    conn.close()
    return len(new_items), len(changed_items)

# ======================================
# 2단계: 상세 크롤링 (변경 건만)
# ======================================
def crawl_details_for_ids(session, id_list, label="상세"):
    """지정된 ID 목록만 상세 크롤링"""
    if not id_list:
        print(f"\n  [{label}] 수집할 건 없음.")
        return 0
    
    print(f"\n{'='*60}")
    print(f"[2단계] {label}: {len(id_list)}건 상세 크롤링")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(DB_PATH)
    success = 0
    
    for idx, internal_id in enumerate(id_list):
        try:
            detail = parse_detail_page(session, internal_id)
            if detail:
                # fail_count 계산
                bid_history = detail.get('bid_history', [])
                fail_count = sum(1 for bid in bid_history if '유찰' in bid.get('result', ''))
                detail['fail_count'] = fail_count
                
                # DB에 상세 업데이트
                from crawler import save_detail_to_db
                save_detail_to_db(detail)
                success += 1
                
                if (idx + 1) % 10 == 0:
                    print(f"  {idx+1}/{len(id_list)} 진행중 (성공:{success})")
            else:
                print(f"  ID:{internal_id} - 상세 페이지 없음")
            
            time.sleep(DELAY_DETAIL)
        except Exception as e:
            print(f"  ID:{internal_id} 오류: {e}")
    
    conn.close()
    print(f"  ✅ 상세 크롤링 완료: {success}/{len(id_list)}건 성공")
    return success

def crawl_details_parallel_for_ids(id_list, num_workers=NUM_DETAIL_WORKERS):
    """병렬 상세 크롤링"""
    if not id_list:
        return 0
    
    print(f"\n{'='*60}")
    print(f"[2단계] 상세 크롤링 {len(id_list)}건 ({num_workers}개 워커)")
    print(f"{'='*60}")
    
    chunk_size = max(1, len(id_list) // num_workers)
    chunks = [id_list[i:i+chunk_size] for i in range(0, len(id_list), chunk_size)]
    
    def worker(worker_id, ids):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        })
        if not login(session):
            return 0
        
        success = 0
        for internal_id in ids:
            try:
                detail = parse_detail_page(session, internal_id)
                if detail:
                    bid_history = detail.get('bid_history', [])
                    fail_count = sum(1 for bid in bid_history if '유찰' in bid.get('result', ''))
                    detail['fail_count'] = fail_count
                    from crawler import save_detail_to_db
                    save_detail_to_db(detail)
                    success += 1
                time.sleep(DELAY_DETAIL)
            except Exception as e:
                pass
        return success
    
    total_success = 0
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        for wid, chunk in enumerate(chunks):
            f = executor.submit(worker, wid + 1, chunk)
            futures[f] = wid + 1
        
        for f in as_completed(futures):
            try:
                total_success += f.result()
            except Exception as e:
                print(f"  워커 오류: {e}")
    
    print(f"  ✅ 상세 크롤링 완료: {total_success}/{len(id_list)}건")
    return total_success

# ======================================
# 크롤링 로그
# ======================================
def start_crawl_log(crawl_type='incremental'):
    """크롤링 시작 로그"""
    os.makedirs(LOG_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO crawl_log (crawl_type, started_at, status)
        VALUES (?, datetime('now', '+9 hours'), 'running')
    ''', (crawl_type,))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def finish_crawl_log(log_id, new_items=0, updated_items=0, total_scanned=0, detail_scraped=0, error_message=''):
    """크롤링 완료 로그"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE crawl_log SET
            finished_at = datetime('now', '+9 hours'),
            new_items = ?,
            updated_items = ?,
            total_scanned = ?,
            detail_scraped = ?,
            status = ?,
            error_message = ?
        WHERE id = ?
    ''', (new_items, updated_items, total_scanned, detail_scraped,
          'error' if error_message else 'completed', error_message, log_id))
    conn.commit()
    conn.close()

# ======================================
# 메인: 증분 크롤링
# ======================================
def crawl_incremental(scan_pages=10, full_detail=False, sno=''):
    """증분 크롤링 메인"""
    print("=" * 60)
    print(f"gfauction.co.kr 증분 크롤러")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"모드: 증분 (최근 {scan_pages}페이지 스캔)")
    print("=" * 60)
    
    log_id = start_crawl_log('incremental')
    
    try:
        # DB 초기화 (테이블 확인만)
        init_db()
        
        # 세션 & 로그인
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        })
        
        if not login(session):
            raise Exception("로그인 실패")
        
        # ===== 1단계: 리스트 빠른 스캔 =====
        new_items, changed_items, total_scanned = scan_list_pages(session, max_pages=scan_pages, sno=sno)
        
        # 리스트 결과 DB 반영
        new_count, changed_count = process_list_results(new_items, changed_items)
        
        # ===== 2단계: 상세 크롤링 =====
        # 수집할 ID 목록
        detail_ids = []
        
        # 신규 건은 항상 상세 수집
        detail_ids.extend([int(item.get('internal_id', 0)) for item in new_items])
        
        # 변경 건: 상태가 변경된 건은 상세 재수집
        if full_detail:
            # --full-detail: 모든 변경 건 상세 재수집
            detail_ids.extend([int(item.get('internal_id', 0)) for item, _ in changed_items])
        else:
            # 기본: 상태 변경 건만 상세 재수집
            for item, changes in changed_items:
                status_changed = any(c['field'] == 'status' for c in changes)
                price_changed = any(c['field'] in ('min_price', 'sale_price') for c in changes)
                if status_changed or price_changed:
                    detail_ids.append(int(item.get('internal_id', 0)))
        
        # 중복 제거
        detail_ids = list(set(detail_ids))
        
        # 상세 크롤링 실행
        if len(detail_ids) > 20:
            detail_success = crawl_details_parallel_for_ids(detail_ids)
        else:
            detail_success = crawl_details_for_ids(session, detail_ids)
        
        # ===== 변경된 ID를 JSON 파일로 저장 (generate_site.py에서 사용) =====
        all_changed_ids = []
        all_changed_ids.extend([int(item.get('internal_id', 0)) for item in new_items])
        all_changed_ids.extend([int(item.get('internal_id', 0)) for item, _ in changed_items])
        all_changed_ids = list(set(all_changed_ids))
        
        changed_ids_path = os.path.join(BASE_DIR, 'data', 'changed_ids.json')
        with open(changed_ids_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ids': all_changed_ids
            }, f, ensure_ascii=False)
        print(f"  💾 변경 ID 저장: {len(all_changed_ids)}건 → data/changed_ids.json")
        
        # ===== 결과 요약 =====
        print(f"\n{'='*60}")
        print(f"📊 증분 크롤링 결과:")
        print(f"  스캔: {total_scanned}건")
        print(f"  🆕 신규: {new_count}건")
        print(f"  🔄 변경: {changed_count}건")
        print(f"  📋 상세 수집: {detail_success}건")
        print(f"{'='*60}")
        
        # 로그 완료
        finish_crawl_log(log_id,
            new_items=new_count,
            updated_items=changed_count,
            total_scanned=total_scanned,
            detail_scraped=detail_success)
        
        # 변경 내역 상세 출력
        if changed_items:
            print(f"\n📝 변경 상세 내역:")
            for item, changes in changed_items[:20]:  # 최대 20건까지만 출력
                cn = item.get('case_number', '?')
                for c in changes:
                    print(f"  [{cn}] {c['label']}: {c['old']} → {c['new']}")
            if len(changed_items) > 20:
                print(f"  ... 외 {len(changed_items) - 20}건")
        
        print(f"\n종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'new': new_count,
            'changed': changed_count,
            'detail': detail_success,
            'scanned': total_scanned,
        }
    
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        finish_crawl_log(log_id, error_message=str(e))
        raise

# ======================================
# 메인
# ======================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='gfauction 증분 크롤러')
    parser.add_argument('--pages', type=int, default=10, help='스캔할 리스트 페이지 수 (기본: 10)')
    parser.add_argument('--full-detail', action='store_true', help='모든 변경 건의 상세 재수집')
    parser.add_argument('--sno', type=str, default='', help='연도 필터 (예: 2026)')
    args = parser.parse_args()
    
    crawl_incremental(scan_pages=args.pages, full_detail=args.full_detail, sno=args.sno)