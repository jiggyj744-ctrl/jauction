"""워커 1개 추가 실행 - 현재 실행중인 크롤러와 병렬로 동작"""
import sys
sys.path.insert(0, r"C:\Users\Work\AppData\Local\Programs\Python\Python312\Lib\site-packages")

from crawler import init_db, crawl_details_parallel

if __name__ == '__main__':
    print("=" * 60)
    print("워커 1개 추가 실행")
    print("=" * 60)
    init_db()
    crawl_details_parallel(num_workers=1)
    print("완료!")