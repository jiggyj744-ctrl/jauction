import sqlite3
import requests
import os
import time

from config import DB_PATH

# 카카오 REST API 키 (발급 받아 설정해야 함)
# KAKAO_REST_API_KEY 환경변수가 설정되어 있으면 사용, 없으면 빈 문자열
KAKAO_API_KEY = os.environ.get('KAKAO_REST_API_KEY', '')

def geocode_address(address):
    """주소를 위경도 좌표로 변환"""
    if not KAKAO_API_KEY:
        return None, None
        
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('documents'):
                doc = data['documents'][0]
                return float(doc['y']), float(doc['x'])  # lat, lon
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
        
    return None, None

def run_geocoding_batch(limit=500):
    print("주소 위경도 변환 시작...")
    if not KAKAO_API_KEY:
        print("경고: KAKAO_REST_API_KEY 환경변수가 설정되어 있지 않아 위경도 변환을 건너뜁니다.")
        return
        
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # geocoded=0 인 항목들만
        cursor.execute('''
            SELECT internal_id, address
            FROM auction_items
            WHERE address IS NOT NULL AND address != '' AND geocoded = 0
            LIMIT ?
        ''', (limit,))
        
        items = cursor.fetchall()
        print(f"변환 대상 물건: {len(items)}건")
        
        success_count = 0
        for internal_id, address in items:
            clean_addr = address.split(',')[0].strip()
            
            lat, lon = geocode_address(clean_addr)
            if lat and lon:
                cursor.execute('''
                    UPDATE auction_items
                    SET lat = ?, lon = ?, geocoded = 1
                    WHERE internal_id = ?
                ''', (lat, lon, internal_id))
                success_count += 1
            else:
                cursor.execute('UPDATE auction_items SET geocoded = 2 WHERE internal_id = ?', (internal_id,))
                
            time.sleep(0.1)
            
        conn.commit()
    print(f"주소 변환 완료: {success_count}건 좌표 반영됨.")

if __name__ == '__main__':
    run_geocoding_batch()
