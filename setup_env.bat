@echo off
chcp 65001

REM Log file setup
set LOGFILE=setup_env_log.txt
echo Starting setup_env.bat > %LOGFILE%
echo ===================================== >> %LOGFILE%

REM 파일명: setup_env.bat

REM 경로 설정 및 유효성 검사 함수
:validate_path
if not exist "%1\tool\Tesseract-OCR\tesseract.exe" (
    echo Invalid path: %1 >> %LOGFILE%
    echo Invalid path: %1
    pause
    exit /b 1
)
exit /b 0

REM 경로 감지 함수
:detect_path
setlocal enabledelayedexpansion
set found_drive=0

REM Checking if files are in the current directory (C:\Users\rhkrt\Documents\GitHub)
if exist "%~dp0tool\Tesseract-OCR\tesseract.exe" (
    set DRIVE_PATH=%~dp0
    echo Found files in the current directory: %DRIVE_PATH% >> %LOGFILE%
    echo Found files in the current directory: %DRIVE_PATH%
    goto :drive_found
)

REM USB 드라이브 경로 감지
for %%a in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist %%a:\AI-M1\tool\Tesseract-OCR\tesseract.exe (
        set USB_DRIVE=%%a:\
        set found_drive=1
        echo Found USB drive at %%a: >> %LOGFILE%
        echo Found USB drive at %%a:
        goto :found_drive
    )
)
if !found_drive! equ 0 (
    echo USB drive not found. Checking C and D drives. >> %LOGFILE%
    echo USB drive not found. Checking C and D drives.
    set DRIVE_PATHS=C:\AI-M1 D:\AI-M1
    for %%d in (%DRIVE_PATHS%) do (
        call :validate_path "%%d"
        if !errorlevel! equ 0 (
            set DRIVE_PATH=%%d
            echo Found drive at %%d >> %LOGFILE%
            echo Found drive at %%d
            goto :drive_found
        )
    )
    echo "Tesseract를 찾을 수 없습니다. 올바른 경로를 입력하세요." >> %LOGFILE%
    echo "Tesseract를 찾을 수 없습니다. 올바른 경로를 입력하세요."
    pause
    exit /b 1
) else (
    set DRIVE_PATH=%USB_DRIVE%AI-M1
)
goto :eof

:found_drive
goto :eof

:drive_found
goto :eof

REM 경로 감지 및 설정
call :detect_path

REM Tesseract 및 Poppler 경로 설정
set TESSERACT_PATH=%DRIVE_PATH%\tool\Tesseract-OCR\tesseract.exe
set POPPLER_PATH=%DRIVE_PATH%\tool\poppler-24.08.0\Library\bin
set PATH=%TESSERACT_PATH%;%POPPLER_PATH%;%PATH%

echo Tesseract 경로 설정 완료: %TESSERACT_PATH% >> %LOGFILE%
echo Poppler 경로 설정 완료: %POPPLER_PATH% >> %LOGFILE%

REM Python 버전 확인 및 업데이트
echo Python 버전 확인 및 업데이트... >> %LOGFILE%

REM 현재 Python 버전 확인
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1 ^| findstr /r "[0-9]\.[0-9]"') do (
    set CURRENT_PYTHON_VERSION=%%a
)

if defined CURRENT_PYTHON_VERSION (
    echo 현재 Python 버전: %CURRENT_PYTHON_VERSION% >> %LOGFILE%
    echo 현재 Python 버전: %CURRENT_PYTHON_VERSION%
    pause
    REM Python 최신 버전 확인 및 업데이트
    for /f "tokens=3 delims==" %%a in ('pip index versions pip ^| findstr /r "Latest:"') do (
        set LATEST_PIP_VERSION=%%a
        set LATEST_PIP_VERSION=%LATEST_PIP_VERSION:Latest: =%
        set LATEST_PIP_VERSION=%LATEST_PIP_VERSION:~1,-1%
    )
    if defined LATEST_PIP_VERSION (
        echo pip 최신 버전: %LATEST_PIP_VERSION% >> %LOGFILE%
        echo pip 최신 버전: %LATEST_PIP_VERSION%
        set /p update_python_choice="Python 및 pip를 업데이트하시겠습니까? (y/n): "
        if /i "%update_python_choice%"=="y" (
            echo Python 및 pip 업데이트 시작... >> %LOGFILE%
            echo Python 및 pip 업데이트 시작...
            python -m ensurepip --upgrade
            if errorlevel 1 (
                echo Python 업데이트에 실패했습니다. 관리자 권한으로 실행하거나 Python 설치를 확인하세요. >> %LOGFILE%
                echo Python 업데이트에 실패했습니다. 관리자 권한으로 실행하거나 Python 설치를 확인하세요.
                pause
                exit /b 1
            )
            python -m pip install --upgrade pip
            if errorlevel 1 (
                echo pip 업데이트에 실패했습니다. >> %LOGFILE%
                echo pip 업데이트에 실패했습니다.
                pause
                exit /b 1
            )
            echo Python 및 pip 업데이트 완료. >> %LOGFILE%
            echo Python 및 pip 업데이트 완료.
        ) else (
            echo Python 및 pip 업데이트를 건너뜁니다. >> %LOGFILE%
            echo Python 및 pip 업데이트를 건너뜁니다.
        )
    ) else (
        echo pip 최신 버전 정보를 가져오는 데 실패했습니다. >> %LOGFILE%
        echo pip 최신 버전 정보를 가져오는 데 실패했습니다.
    )
) else (
    echo Python이 설치되어 있지 않습니다. Python을 설치해주세요. >> %LOGFILE%
    echo Python이 설치되어 있지 않습니다. Python을 설치해주세요.
    pause
    exit /b 1
)

REM kocrd 패키지 경로 추가
set PYTHONPATH=%PYTHONPATH%;%~dp0kocrd

REM 기본 라이브러리 설치
echo 기본 Python 라이브러리 설치 중... >> %LOGFILE%
echo 기본 Python 라이브러리 설치 중...
pip install PyQt5 opencv-python pytesseract pdf2image fpdf tensorflow flask python-dotenv chardet pika tf-keras
if errorlevel 1 (
    echo 일부 라이브러리 설치에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
    echo 일부 라이브러리 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo 기본 라이브러리 설치 완료. >> %LOGFILE%
echo 기본 라이브러리 설치 완료.

REM sentence-transformers 설치 관리
echo sentence-transformers 설치 관리... >> %LOGFILE%
echo sentence-transformers 설치 관리...
set SENTENCE_TRANSFORMER_PATH=%~dp0tool\Sentence_Transformer

REM 폴더가 없으면 생성
if not exist "%SENTENCE_TRANSFORMER_PATH%\" mkdir "%SENTENCE_TRANSFORMER_PATH%"

REM 설치된 sentence-transformers 버전 확인
echo 설치된 sentence-transformers 버전 확인 중... >> %LOGFILE%
echo 설치된 sentence-transformers 버전 확인 중...
if exist "%SENTENCE_TRANSFORMER_PATH%\sentence_transformers\__init__.py" (
    for /f "tokens=3 delims==" %%a in ('python -c "import sentence_transformers; print(sentence_transformers.__version__)" 2^>nul') do (
        set INSTALLED_VERSION=%%a
    )
    if defined INSTALLED_VERSION (
        echo 설치된 버전: %INSTALLED_VERSION% >> %LOGFILE%
        echo 설치된 버전: %INSTALLED_VERSION%
        REM 최신 버전 확인
        for /f "tokens=3 delims==" %%a in ('pip index versions sentence-transformers ^| findstr /r "Latest:"') do (
            set LATEST_VERSION=%%a
            set LATEST_VERSION=%LATEST_VERSION:Latest: =%
            set LATEST_VERSION=%LATEST_VERSION:~1,-1%
        )
        if defined LATEST_VERSION (
            echo 최신 버전: %LATEST_VERSION% >> %LOGFILE%
            echo 최신 버전: %LATEST_VERSION%
            REM 업데이트 여부 확인
            if "%INSTALLED_VERSION%" NEQ "%LATEST_VERSION%" (
                set /p update_choice="sentence-transformers의 새 버전(%LATEST_VERSION%)이 있습니다. 업데이트하시겠습니까? (y/n): "
                if /i "%update_choice%"=="y" (
                    echo sentence-transformers 업데이트 중... >> %LOGFILE%
                    echo sentence-transformers 업데이트 중...
                    pip install --target "%SENTENCE_TRANSFORMER_PATH%" --upgrade sentence-transformers --no-user
                    if errorlevel 1 (
                        echo sentence-transformers 업데이트에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
                        echo sentence-transformers 업데이트에 실패했습니다. 오류 메시지를 확인하세요.
                        pause
                        exit /b 1
                    )
                    echo sentence-transformers 업데이트 완료. >> %LOGFILE%
                    echo sentence-transformers 업데이트 완료.
                ) else (
                    echo sentence-transformers 업데이트를 건너뜁니다. >> %LOGFILE%
                    echo sentence-transformers 업데이트를 건너뜁니다.
                )
            ) else (
                echo sentence-transformers가 최신 버전입니다. >> %LOGFILE%
                echo sentence-transformers가 최신 버전입니다.
            )
        ) else (
            echo 최신 버전 정보를 가져오는 데 실패했습니다. >> %LOGFILE%
            echo 최신 버전 정보를 가져오는 데 실패했습니다.
        )
    ) else (
        echo sentence-transformers가 설치되어 있지 않습니다. >> %LOGFILE%
        echo sentence-transformers가 설치되어 있지 않습니다.
    )
) else (
    REM sentence-transformers 설치
    set /p install_type="sentence-transformers 설치 유형을 선택하세요 (1: 일반 설치, 2: 개발용 설치): "
    if "%install_type%"=="1" (
        pip install --target "%SENTENCE_TRANSFORMER_PATH%" sentence-transformers --no-user
    ) else if "%install_type%"=="2" (
        pip install --target "%SENTENCE_TRANSFORMER_PATH%" "sentence-transformers[dev]" --no-user
    ) else (
        echo 잘못된 선택입니다. 일반 설치를 진행합니다. >> %LOGFILE%
        echo 잘못된 선택입니다. 일반 설치를 진행합니다.
        pip install --target "%SENTENCE_TRANSFORMER_PATH%" sentence-transformers --no-user
    )
    if errorlevel 1 (
        echo sentence-transformers 설치에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
        echo sentence-transformers 설치에 실패했습니다. 오류 메시지를 확인하세요.
        pause
        exit /b 1
    )
    echo sentence-transformers 설치 완료. >> %LOGFILE%
    echo sentence-transformers 설치 완료.
)

REM PyMuPDF 설치
echo PyMuPDF 설치 중... >> %LOGFILE%
echo PyMuPDF 설치 중...
pip install pymupdf
if errorlevel 1 (
    echo PyMuPDF 설치에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
    echo PyMuPDF 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo PyMuPDF 설치 완료. >> %LOGFILE%
echo PyMuPDF 설치 완료.

REM 설정 확인
echo 현재 PATH: %PATH% >> %LOGFILE%
echo 현재 PATH: %PATH%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다. >> %LOGFILE%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다.

pause