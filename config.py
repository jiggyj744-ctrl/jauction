"""
프로젝트 공통 설정
- 로그인 정보, 경로, 딜레이 등 중앙 관리
- 모든 모듈은 여기서 DB_PATH 등을 import하여 사용
"""
import os

# 프로젝트 기본 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env 파일 자동 로드 (있으면 값 덮어쓰기)
_env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                _key = _key.strip()
                _val = _val.strip()
                if _key and _key not in os.environ:
                    os.environ[_key] = _val

# DB 경로 (Single Source of Truth)
DB_PATH = os.path.join(BASE_DIR, 'data', 'auction.db')

# 이미지 저장 경로
IMAGE_BASE_DIR = os.path.join(BASE_DIR, 'images')

# 로그 디렉토리
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 사이트 설정
BASE_URL = 'https://gfauction.co.kr'
SITE_NAME = 'jauction'
SITE_URL = 'https://jiggyj744-ctrl.github.io/jauction'
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '010-6899-1601')

# 로그인 정보 (환경변수에서 읽거나 기본값 사용)
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