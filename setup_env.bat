<<<<<<< HEAD
@echo off
chcp 65001

REM Log file setup
echo ===================================== >> %LOGFILE%

REM Python 버전 확인 및 업데이트 (수정)
echo Python 버전 확인 및 업데이트...

REM Python 버전 확인
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1 ^| findstr /r "[0-9]\.[0-9]"') do (
    set CURRENT_PYTHON_VERSION=%%a
)

if not defined CURRENT_PYTHON_VERSION (
    echo Python이 설치되어 있지 않습니다. Python을 설치해주세요.
    pause
    exit /b 1
)

echo 현재 Python 버전: %CURRENT_PYTHON_VERSION%

REM 가상 환경 생성 및 활성화 (수정)
echo 가상 환경 생성 및 활성화...
python -m venv .venv
if errorlevel 1 (
    echo 가상 환경 생성에 실패했습니다.
    pause
    exit /b 1
)

.venv\Scripts\activate

echo 가상 환경 활성화 완료. >> %LOGFILE%

REM pip 최신 버전 확인 및 업데이트
echo pip 최신 버전 확인 및 업데이트... >> %LOGFILE%
python -m pip install --upgrade pip
if errorlevel 1 (
    echo pip 업데이트에 실패했습니다.
    pause
    exit /b 1
)
echo pip 업데이트 완료. >> %LOGFILE%

REM 필요한 모듈 설치 (requirements.txt 활용)
echo 필요한 모듈 설치 중... >> %LOGFILE%

REM requirements.txt 파일 경로 설정
set REQUIREMENTS_FILE_PATH="%~dp0config\requirements.txt"

REM requirements.txt 파일이 존재하는지 확인
if not exist "%REQUIREMENTS_FILE_PATH%" (
    echo requirements.txt 파일이 존재하지 않습니다.
    pause
    exit /b 1
)

pip install -r "%REQUIREMENTS_FILE_PATH%"
if errorlevel 1 (
    echo 일부 모듈 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo 필요한 모듈 설치 완료. >> %LOGFILE%


REM sentence-transformers 설치 관리 (자동 업데이트)
echo sentence-transformers 설치 관리...

REM sentence-transformers가 설치되어 있는지 확인
python -c "import sentence_transformers" 2>nul
if errorlevel 1 goto :install_sentence_transformers

REM 설치된 sentence-transformers 버전 확인
echo 설치된 sentence-transformers 버전 확인 중... >> %LOGFILE%
echo 설치된 sentence-transformers 버전 확인 중...
for /f "tokens=3 delims==" %%a in ('python -c "import sentence_transformers; print(sentence_transformers.__version__)" 2^>nul') do (
    set INSTALLED_VERSION=%%a
)

REM 최신 버전 확인
for /f "tokens=3 delims==" %%a in ('pip index versions sentence-transformers ^| findstr /r "Latest:"') do (
    set LATEST_VERSION=%%a
    set LATEST_VERSION=%LATEST_VERSION:Latest: =%
    set LATEST_VERSION=%LATEST_VERSION:~1,-1%
)

if not defined LATEST_VERSION (
    echo sentence-transformers 최신 버전 정보를 가져오는 데 실패했습니다.
    goto :install_sentence_transformers
}

echo 설치된 버전: %INSTALLED_VERSION%
echo 최신 버전: %LATEST_VERSION%

REM 최신 버전이 아니면 업데이트
if "%INSTALLED_VERSION%" NEQ "%LATEST_VERSION%" goto :install_sentence_transformers

echo sentence-transformers가 최신 버전입니다.
goto :eof

:install_sentence_transformers
REM sentence-transformers 설치 또는 업데이트
pip install --target "%SENTENCE_TRANSFORMER_PATH%" --upgrade sentence-transformers --no-user
if errorlevel 1 (
    echo sentence-transformers 설치 또는 업데이트에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo sentence-transformers 설치 또는 업데이트 완료.

REM PyMuPDF 설치 (오류 발생 시 계속 진행)
echo PyMuPDF 설치 중... >> %LOGFILE%
echo PyMuPDF 설치 중...
pip install pymupdf
if errorlevel 1 (
    echo PyMuPDF 설치에 실패했습니다. 오류 메시지를 확인하세요. 계속 진행합니다.
}
echo PyMuPDF 설치 완료. >> %LOGFILE%
echo PyMuPDF 설치 완료.

REM 설정 확인
echo 현재 PATH: %PATH%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다.

=======
@echo off
chcp 65001

REM 파일명: setup_env.bat

REM USB 드라이브 경로 감지
for %%a in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist %%a:\AI-M1\tool\Tesseract-OCR\tesseract.exe (
        set USB_DRIVE=%%a:\
        goto :found_drive
    )
)

:found_drive
if not defined USB_DRIVE (
    echo USB 드라이브를 찾을 수 없습니다.
    pause
    exit /b 1
)

REM Tesseract 및 Poppler 경로 설정
set TESSERACT_PATH=%USB_DRIVE%AI-M1\tool\Tesseract-OCR\tesseract.exe
set POPPLER_PATH=%USB_DRIVE%AI-M1\tool\poppler-24.08.0\Library\bin
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

.venv\Scripts\activate
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

>>>>>>> 0b45195 (S)
pause