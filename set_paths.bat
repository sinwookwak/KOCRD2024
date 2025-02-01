@echo off
chcp 65001

REM Log file setup
set LOGFILE=set_paths_log.txt
echo Starting set_paths.bat > %LOGFILE%
echo ===================================== >> %LOGFILE%

REM Tesseract 경로 설정
echo Tesseract 경로를 선택하세요.
echo 1. 개발자 모드 (Github)
echo 2. 개발자 모드 (경로 입력)
echo 3. USB 외장 드라이브

set /p choice="선택 (숫자 입력): "

if "%choice%"=="1" (
    set TESSERACT_EXE_PATH="C:\Users\rhkrt\Documents\GitHub\tool\Tesseract-OCR\tesseract.exe"
    goto :validate_tesseract_path
} else if "%choice%"=="2" (
    set /p TESSERACT_EXE_PATH="Tesseract 경로를 입력하세요: "
    goto :validate_tesseract_path
} else if "%choice%"=="3" {
    REM USB 드라이브 경로 감지 (수정)
    setlocal enabledelayedexpansion
    set found_drives=0
    set drive_paths=
    for %%a in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        if exist %%a:\AI-M1\tool\Tesseract-OCR\tesseract.exe (
            for /f "tokens=2 delims=: " %%b in ('vol %%a: 2^>nul') do (
                set /a found_drives+=1
                set drive_paths=!drive_paths! "%%a:\AI-M1 (%%b)"
                echo Found USB drive at %%a:\AI-M1 (%%b) >> %LOGFILE%
            )
        )
    )

    if %found_drives% equ 0 (
        echo USB 드라이브를 찾을 수 없습니다. >> %LOGFILE%
        echo USB 드라이브를 찾을 수 없습니다.
        pause
        exit /b 1
    } else if %found_drives% equ 1 {
        for %%p in (%drive_paths%) do set TESSERACT_EXE_PATH=%%p\tool\Tesseract-OCR\tesseract.exe
        goto :validate_tesseract_path
    } else {
        echo 여러 개의 USB 드라이브가 발견되었습니다. 사용할 드라이브를 선택하세요. >> %LOGFILE%
        echo 여러 개의 USB 드라이브가 발견되었습니다. 사용할 드라이브를 선택하세요.
        set count=0
        for %%p in (%drive_paths%) do (
            set /a count+=1
            echo [!count!] %%p
            echo [!count!] %%p >> %LOGFILE%
        )
        set /p choice="선택 (숫자 입력): "
        set count=0
        for %%p in (%drive_paths%) do (
            set /a count+=1
            if !count! equ %choice% set TESSERACT_EXE_PATH=%%p\tool\Tesseract-OCR\tesseract.exe
        )
        goto :validate_tesseract_path
    }
    endlocal
} else {
    echo 잘못된 선택입니다. >> %LOGFILE%
    echo 잘못된 선택입니다.
    pause
    exit /b 1
}

:validate_tesseract_path
if not exist "%TESSERACT_EXE_PATH%" (
    echo Invalid path: %TESSERACT_EXE_PATH% >> %LOGFILE%
    echo Invalid path: %TESSERACT_EXE_PATH%
    pause
    exit /b 1
)

echo Tesseract 경로: %TESSERACT_EXE_PATH% >> %LOGFILE%
echo Tesseract 경로: %TESSERACT_EXE_PATH%

REM Poppler 경로 설정 (상대 경로 사용)
set POPPLER_EXE_PATH="%~dp0tool\poppler-24.08.0\Library\bin\pdftoppm.exe"

REM sentence-transformers 경로 설정 (상대 경로 사용)
set SENTENCE_TRANSFORMERS_PATH="%~dp0tool\Sentence_Transformer"

echo Poppler 경로: %POPPLER_EXE_PATH% >> %LOGFILE%
echo Poppler 경로: %POPPLER_EXE_PATH%

echo sentence-transformers 경로: %SENTENCE_TRANSFORMERS_PATH% >> %LOGFILE%
echo sentence-transformers 경로: %SENTENCE_TRANSFORMERS_PATH%

REM 환경 변수 설정 (중복 방지)
echo "%PATH%" | findstr /i "%TESSERACT_EXE_PATH%" >nul
if errorlevel 1 set PATH=%TESSERACT_EXE_PATH%;%PATH%

echo "%PATH%" | findstr /i "%POPPLER_EXE_PATH%" >nul
if errorlevel 1 set PATH=%POPPLER_EXE_PATH%;%PATH%

echo "%PYTHONPATH%" | findstr /i "%SENTENCE_TRANSFORMERS_PATH%" >nul
if errorlevel 1 set PYTHONPATH=%PYTHONPATH%;%SENTENCE_TRANSFORMERS_PATH%

echo "%PYTHONPATH%" | findstr /i "%~dp0kocrd" >nul
if errorlevel 1 set PYTHONPATH=%PYTHONPATH%;%~dp0kocrd

echo 환경 변수 설정 완료. >> %LOGFILE%
echo 환경 변수 설정 완료.

pause