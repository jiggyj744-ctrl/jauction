@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Git 경로 설정
set PATH=C:\Program Files\Git\cmd;%PATH%

echo ============================================================
echo   jauction 데일리 업데이트
echo   시작: %date% %time%
echo ============================================================

cd /d D:\jauction

REM ============================================
REM 1단계: 증분 크롤링
REM ============================================
echo.
echo [1/6] 증분 크롤링 시작...
python crawler_incremental.py --pages 700
if %errorlevel% neq 0 (
    echo ❌ 크롤링 실패! 오류 코드: %errorlevel%
    exit /b 1
)
echo ✅ 크롤링 완료

REM ============================================
REM 2단계: 증분 데이터 보완
REM ============================================
echo.
echo [2/6] 증분 데이터 보완 (fix_all_incremental) 시작...
python scripts\fix_all_incremental.py
if %errorlevel% neq 0 (
    echo ❌ fix_all_incremental 실패! 오류 코드: %errorlevel%
    exit /b 1
)
echo ✅ fix_all_incremental 완료

REM ============================================
REM 3단계: 주소 위경도 변환
REM ============================================
echo.
echo [3/6] 카카오 주소 위경도 변환 시작...
python geocode_batch.py
if %errorlevel% neq 0 (
    echo ❌ 위경도 변환 실패! 오류 코드: %errorlevel%
    exit /b 1
)
echo ✅ 위경도 변환 완료

REM ============================================
REM 4단계: 증분 사이트 생성
REM ============================================
echo.
echo [4/6] 증분 사이트 생성 시작...
python generate_site.py --incremental
if %errorlevel% neq 0 (
    echo ❌ 사이트 생성 실패! 오류 코드: %errorlevel%
    exit /b 1
)
echo ✅ 사이트 생성 완료

REM ============================================
REM 5단계: Git 커밋
REM ============================================
echo.
echo [5/6] Git 커밋...
cd /d D:\jauction
git add docs/
git status --short docs/
git commit -m "daily update %date:/=-%"
if %errorlevel% neq 0 (
    echo ℹ️ 커밋할 변경사항 없음 (이미 최신)
) else (
    echo ✅ 커밋 완료
)

REM ============================================
REM 6단계: Git 푸시
REM ============================================
echo.
echo [6/6] GitHub 푸시...
git push origin master
if %errorlevel% neq 0 (
    echo ❌ 푸시 실패! 네트워크를 확인하세요.
    exit /b 1
)
echo ✅ 푸시 완료

echo.
echo ============================================================
echo   ✅ 데일리 업데이트 완료!
echo   종료: %date% %time%
echo ============================================================
echo.
