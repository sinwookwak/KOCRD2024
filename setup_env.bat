@echo off
chcp 65001

REM Log file setup
set LOGFILE=setup_env_log.txt
echo ===================================== >> %LOGFILE%

REM Python 버전 확인 및 업데이트 (수정)
echo Python 버전 확인 및 업데이트... >> %LOGFILE%
echo Python 버전 확인 및 업데이트...

REM Python 버전 확인
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1 ^| findstr /r "[0-9]\.[0-9]"') do (
    set CURRENT_PYTHON_VERSION=%%a
)

if not defined CURRENT_PYTHON_VERSION (
    echo Python이 설치되어 있지 않습니다. Python을 설치해주세요. >> %LOGFILE%
    echo Python이 설치되어 있지 않습니다. Python을 설치해주세요.
    pause
    exit /b 1
)

echo 현재 Python 버전: %CURRENT_PYTHON_VERSION% >> %LOGFILE%
echo 현재 Python 버전: %CURRENT_PYTHON_VERSION%

REM 가상 환경 생성 및 활성화 (수정)
echo 가상 환경 생성 및 활성화... >> %LOGFILE%
python -m venv .venv
if errorlevel 1 (
    echo 가상 환경 생성에 실패했습니다. >> %LOGFILE%
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
    echo pip 업데이트에 실패했습니다. >> %LOGFILE%
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
    echo requirements.txt 파일이 존재하지 않습니다. >> %LOGFILE%
    echo requirements.txt 파일이 존재하지 않습니다.
    pause
    exit /b 1
)

pip install -r "%REQUIREMENTS_FILE_PATH%"
if errorlevel 1 (
    echo 일부 모듈 설치에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
    echo 일부 모듈 설치에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo 필요한 모듈 설치 완료. >> %LOGFILE%


REM sentence-transformers 설치 관리 (자동 업데이트)
echo sentence-transformers 설치 관리... >> %LOGFILE%
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
    echo sentence-transformers 최신 버전 정보를 가져오는 데 실패했습니다. >> %LOGFILE%
    echo sentence-transformers 최신 버전 정보를 가져오는 데 실패했습니다.
    goto :install_sentence_transformers
}

echo 설치된 버전: %INSTALLED_VERSION% >> %LOGFILE%
echo 설치된 버전: %INSTALLED_VERSION%
echo 최신 버전: %LATEST_VERSION% >> %LOGFILE%
echo 최신 버전: %LATEST_VERSION%

REM 최신 버전이 아니면 업데이트
if "%INSTALLED_VERSION%" NEQ "%LATEST_VERSION%" goto :install_sentence_transformers

echo sentence-transformers가 최신 버전입니다. >> %LOGFILE%
echo sentence-transformers가 최신 버전입니다.
goto :eof

:install_sentence_transformers
REM sentence-transformers 설치 또는 업데이트
pip install --target "%SENTENCE_TRANSFORMER_PATH%" --upgrade sentence-transformers --no-user
if errorlevel 1 (
    echo sentence-transformers 설치 또는 업데이트에 실패했습니다. 오류 메시지를 확인하세요. >> %LOGFILE%
    echo sentence-transformers 설치 또는 업데이트에 실패했습니다. 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo sentence-transformers 설치 또는 업데이트 완료. >> %LOGFILE%
echo sentence-transformers 설치 또는 업데이트 완료.

REM PyMuPDF 설치 (오류 발생 시 계속 진행)
echo PyMuPDF 설치 중... >> %LOGFILE%
echo PyMuPDF 설치 중...
pip install pymupdf
if errorlevel 1 (
    echo PyMuPDF 설치에 실패했습니다. 오류 메시지를 확인하세요. 계속 진행합니다. >> %LOGFILE%
    echo PyMuPDF 설치에 실패했습니다. 오류 메시지를 확인하세요. 계속 진행합니다.
}
echo PyMuPDF 설치 완료. >> %LOGFILE%
echo PyMuPDF 설치 완료.

REM 설정 확인
echo 현재 PATH: %PATH% >> %LOGFILE%
echo 현재 PATH: %PATH%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다. >> %LOGFILE%
echo 환경 변수 변경 사항은 새로운 CMD 창에서 확인 가능합니다.

pause