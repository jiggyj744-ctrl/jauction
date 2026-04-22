import sqlite3
import os

DB_PATH = r'd:\jauction\data\auction.db'

def check_status():
    try:
        if not os.path.exists(DB_PATH):
            print("데이터베이스 파일을 찾을 수 없습니다.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT started_at, finished_at, new_items, updated_items, detail_scraped, status, error_message 
            FROM crawl_log 
            ORDER BY started_at DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        
        if row:
            started_at, finished_at, new, updated, detailed, status, error = row
            print("=" * 50)
            print("  최근 자동 크롤링 결과 요약")
            print("=" * 50)
            
            if status == 'completed':
                print("상태      : [성공] 정상 완료")
            elif status == 'running':
                print("상태      : [진행중] 크롤링이 진행 중입니다")
            else:
                print(f"상태      : [실패] 에러 발생 ({status})")
                
            print(f"시작 시간 : {started_at}")
            print(f"종료 시간 : {finished_at if finished_at else '진행중'}")
            print("-" * 50)
            print(f"신규 물건 수     : {new}건")
            print(f"변경/업데이트 수 : {updated}건")
            print(f"상세정보 수집 수 : {detailed}건")
            
            if error:
                print("-" * 50)
                print(f"에러 메시지: {error}")
                
            print("=" * 50)
        else:
            print("크롤링 기록이 없습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    check_status()
