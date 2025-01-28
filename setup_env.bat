@echo off
chcp 65001

REM 파일명: setup_env.bat

REM 경로 설정 및 유효성 검사 함수
:validate_path
if not exist "%1\tool\Tesseract-OCR\tesseract.exe" (
    exit /b 1
)
exit /b 0

REM USB 드라이브 경로 감지
setlocal enabledelayedexpansion
set found_drive=0

for %%a in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist %%a:\AI-M1\tool\Tesseract-OCR\tesseract.exe (
        set USB_DRIVE=%%a:\
        set found_drive=1
        goto :found_drive
    )
)

:found_drive
if !found_drive! equ 0 (
    echo USB 드라이브를 찾을 수 없습니다. C 드라이브와 D 드라이브를 검사합니다.
    set DRIVE_PATHS=C:\AI-M1 D:\AI-M1

    for %%d in (%DRIVE_PATHS%) do (
        call :validate_path "%%d"
        if !errorlevel! equ 0 (
            set DRIVE_PATH=%%d
            goto :drive_found
        )
    )
    
    echo "Tesseract를 찾을 수 없습니다. 올바른 경로를 입력하세요."
    pause
    exit /b 1
) else (
    set DRIVE_PATH=%USB_DRIVE%AI-M1
)

:drive_found
REM Tesseract 및 Poppler 경로 설정
set TESSERACT_PATH=%DRIVE_PATH%\tool\Tesseract-OCR\tesseract.exe
set POPPLER_PATH=%DRIVE_PATH%\tool\poppler-24.08.0\Library\bin
set PATH=%TESSERACT_PATH%;%POPPLER_PATH%;%PATH%

echo Tesseract 경로 설정 완료: %TESSERACT_PATH%
echo Poppler 경로 설정 완료: %POPPLER_PATH%

REM 가상 환경 생성 및 활성화
if not exist .venv (
    echo 가상 환경 생성 중...
    python -m venv .venv
    if errorlevel 1 (
        echo 가상 환경 생성에 실패했습니다. Python 설치를 확인하세요.
        pause
        exit /b 1
    )
    echo 가상 환경 생성 완료.
)

call .venv\Scripts\activate
if errorlevel 1 (
    echo 가상 환경 활성화에 실패했습니다. .venv 폴더를 확인하세요.
    pause
    exit /b 1
)
echo 가상 환경 활성화 완료.

REM pip 업그레이드
echo pip 업그레이드 중...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo pip 업그레이드에 실패했습니다.
    pause
    exit /b 1
)
echo pip 업그레이드 완료.

REM requirements.txt 파일에서 라이브러리 설치
if exist requirements.txt (
    echo requirements.txt 파일에서 라이브러리 설치 중...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 라이브러리 설치에 실패했습니다. 다음 명령어를 실행하여 자세한 오류 메시지를 확인하세요.
        echo pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo 라이브러리 설치 완료.
) else (
    echo requirements.txt 파일을 찾을 수 없습니다. 필요한 라이브러리를 직접 설치해주세요.
    pause
    exit /b 1
)

REM sentence-transformers 설치 (가상환경 내에 설치)
echo sentence-transformers 설치 중...
pip install sentence-transformers
if errorlevel 1 (
    echo sentence-transformers 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo sentence-transformers 설치 완료.

REM pymupdf 설치
echo pymupdf 설치 중...
pip install pymupdf
if errorlevel 1 (
    echo pymupdf 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo pymupdf 설치 완료.


REM 설정 확인
echo 현재 PATH: %PATH%
echo 현재 PYTHONPATH: %PYTHONPATH%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다.

pause