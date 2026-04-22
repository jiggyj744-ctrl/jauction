"""
프로젝트 공통 설정
- 로그인 정보, 경로, 딜레이 등 중앙 관리
"""
import os

# 프로젝트 기본 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DB 경로
DB_PATH = os.path.join(BASE_DIR, 'data', 'auction.db')

# 이미지 저장 경로
IMAGE_BASE_DIR = os.path.join(BASE_DIR, 'images')

# 로그 디렉토리
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 사이트 설정
BASE_URL = 'https://gfauction.co.kr'
SITE_NAME = 'jauction'
SITE_URL = 'https://jiggyj744-ctrl.github.io/jauction'
PHONE_NUMBER = '010-6899-1601'

# 로그인 정보 (환경변수에서 읽거나 기본값 사용)
import os
LOGIN_ID = os.environ.get('GFAUCTION_ID', '1111')
LOGIN_PW = os.environ.get('GFAUCTION_PW', '1111')

# 크롤링 딜레이 설정
DELAY_LIST = 3.0       # 리스트 페이지 간 딜레이(초)
DELAY_DETAIL = 3.0     # 상세 페이지 간 딜레이(초)
DELAY_IMAGE = 1.0      # 이미지 다운로드 간 딜레이(초)

# 증분 크롤러 딜레이 (빠른 스캔용)
DELAY_LIST_INCREMENTAL = 0.5
DELAY_DETAIL_INCREMENTAL = 0.5
NUM_DETAIL_WORKERS = 20

# 제외 필터
EXCLUDE_STATUS = {'취하', '기각', '정지', '매각'}
EXCLUDE_ITEM_TYPE = {'차량', '묘지'}