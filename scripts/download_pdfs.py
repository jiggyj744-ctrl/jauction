"""PDF 파일 일괄 다운로드 스크립트
- file2.nuriauction.com에서 PDF 다운로드 (로그인 불필요)
- 2워커 + 랜덤 딜레이 1~3초 (차단 방지)
- 이미 다운로드된 파일은 건너뛰기
- HTTP 429/503 감지 시 자동 대기
"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

import sqlite3
import json
import requests
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

DB_PATH = 'data/auction.db'
PDF_DIR = r'd:\jauction\pdfs'
DELAY_MIN = 0.5
DELAY_MAX = 1.5
MAX_RETRIES = 3
NUM_WORKERS = 4

def get_pdf_list():
    """DB에서 다운로드할 PDF URL 목록 가져오기"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT internal_id, pdf_urls FROM auction_items WHERE pdf_urls IS NOT NULL AND pdf_urls != ''")
    rows = c.fetchall()
    conn.close()
    
    pdf_list = []
    for internal_id, pdf_urls_json in rows:
        try:
            urls = json.loads(pdf_urls_json)
            for url in urls:
                pdf_list.append((internal_id, url))
        except:
            pass
    return pdf_list

def download_single_pdf(internal_id, url, session):
    """단일 PDF 다운로드"""
    # 파일명 추출
    filename = url.split('/')[-1]
    if not filename.endswith('.pdf'):
        filename += '.pdf'
    
    # 저장 경로
    save_dir = os.path.join(PDF_DIR, str(internal_id))
    filepath = os.path.join(save_dir, filename)
    
    # 이미 다운로드됨
    if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
        return 'skip', filepath
    
    os.makedirs(save_dir, exist_ok=True)
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=30, stream=True, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,*/*',
            })
            
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'pdf' in content_type.lower() or resp.content[:5] == b'%PDF-':
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    return 'success', filepath
                else:
                    return 'not_pdf', filepath
            elif resp.status_code == 429:
                # Rate limited - 대기 후 재시도
                wait = 30 + random.uniform(5, 15)
                print(f"    ⚠️ 429 Rate Limited. {wait:.0f}초 대기...")
                time.sleep(wait)
            elif resp.status_code == 503:
                wait = 60 + random.uniform(5, 15)
                print(f"    ⚠️ 503 Service Unavailable. {wait:.0f}초 대기...")
                time.sleep(wait)
            else:
                return f'http_{resp.status_code}', filepath
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                return f'error:{str(e)[:50]}', filepath
    
    return 'max_retries', filepath

def pdf_worker(worker_id, task_list):
    """PDF 다운로드 워커"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    })
    
    success = 0
    skip = 0
    fail = 0
    total = len(task_list)
    
    for idx, (internal_id, url) in enumerate(task_list):
        status, filepath = download_single_pdf(internal_id, url, session)
        
        if status == 'success':
            success += 1
        elif status == 'skip':
            skip += 1
        else:
            fail += 1
            if fail <= 5:
                print(f"  [PW{worker_id}] 실패 ID:{internal_id} - {status}")
        
        if (idx + 1) % 100 == 0:
            print(f"  [PW{worker_id}] {idx+1}/{total} 진행 (성공:{success} 스킵:{skip} 실패:{fail})")
        
        # 랜덤 딜레이
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    print(f"  [PW{worker_id}] 완료: 성공:{success} 스킵:{skip} 실패:{fail}")
    return success, skip, fail

def main():
    print("=" * 60)
    print("PDF 파일 일괄 다운로드")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"워커: {NUM_WORKERS}개, 딜레이: {DELAY_MIN}~{DELAY_MAX}초")
    print("=" * 60)
    
    os.makedirs(PDF_DIR, exist_ok=True)
    
    # PDF 목록 가져오기
    print("\n[1] PDF 목록 로딩...")
    pdf_list = get_pdf_list()
    print(f"  총 {len(pdf_list)}개 PDF 파일")
    
    # 이미 다운로드된 건 확인
    already = 0
    to_download = []
    for internal_id, url in pdf_list:
        filename = url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        filepath = os.path.join(PDF_DIR, str(internal_id), filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            already += 1
        else:
            to_download.append((internal_id, url))
    
    print(f"  이미 다운로드됨: {already}개")
    print(f"  다운로드 필요: {len(to_download)}개")
    
    if not to_download:
        print("\n✅ 모든 PDF가 이미 다운로드되었습니다!")
        return
    
    # 예상 시간
    avg_delay = (DELAY_MIN + DELAY_MAX) / 2
    est_minutes = len(to_download) * avg_delay / NUM_WORKERS / 60
    print(f"  예상 소요: ~{est_minutes:.0f}분 ({est_minutes/60:.1f}시간)")
    
    # 워커로 분할
    chunk_size = len(to_download) // NUM_WORKERS + 1
    chunks = [to_download[i:i+chunk_size] for i in range(0, len(to_download), chunk_size)]
    
    print(f"\n[2] 다운로드 시작 ({NUM_WORKERS}워커)...\n")
    
    total_success = 0
    total_skip = 0
    total_fail = 0
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {}
        for wid, chunk in enumerate(chunks):
            f = executor.submit(pdf_worker, wid + 1, chunk)
            futures[f] = wid + 1
        
        for f in as_completed(futures):
            wid = futures[f]
            try:
                success, skip, fail = f.result()
                total_success += success
                total_skip += skip
                total_fail += fail
            except Exception as e:
                print(f"  [PW{wid}] 오류: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"PDF 다운로드 완료!")
    print(f"  성공: {total_success}")
    print(f"  스킵: {total_skip} (이미 있음)")
    print(f"  실패: {total_fail}")
    print(f"  종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()