@echo off
chcp 65001 >nul
echo ========================================
echo Git Manager - 실행 파일 빌드
echo ========================================
echo.

:: Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo 오류: Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다
    pause
    exit /b 1
)

:: 버전 정보 추출
echo 버전 정보 확인 중...
for /f "tokens=2 delims==" %%a in ('python -c "exec(open('git_manager.py').read()); print(__version__)"') do set VERSION=%%a
set VERSION=%VERSION: =%
set VERSION=%VERSION:"=%
echo 현재 버전: v%VERSION%
echo.

:: 의존성 설치
echo 의존성 설치 중...
pip install -r requirements.txt --quiet
echo.

:: 빌드 실행
echo 실행 파일 빌드 중...
echo 출력 파일: GitManager_v%VERSION%.exe
pyinstaller --onefile --windowed --name="GitManager_v%VERSION%" git_manager.py
echo.

:: 빌드 결과 확인
if exist "dist\GitManager_v%VERSION%.exe" (
    echo ========================================
    echo 빌드 성공!
    echo 실행 파일 위치: dist\GitManager_v%VERSION%.exe
    echo ========================================
    echo.
    echo 파일 정보:
    dir "dist\GitManager_v%VERSION%.exe" | findstr "GitManager"
) else (
    echo ========================================
    echo 빌드 실패! 위의 오류 메시지를 확인하세요.
    echo ========================================
)

echo.
pause
