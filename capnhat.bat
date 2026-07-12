@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ==================================================================
REM  capnhat.bat - Update the family tree site with one action.
REM
REM  Usage:  drag-drop the new .ged file onto this file.
REM
REM  Steps: backup -> convert+filter -> safety check -> confirm -> push
REM  If any step fails, it STOPS. It never pushes bad data.
REM
REM  NOTE: This file must stay pure ASCII (no Vietnamese accents).
REM  Windows CMD reads .bat in a legacy codepage; UTF-8 accents get
REM  mangled and CMD tries to run the garbage as commands.
REM ==================================================================

echo.
echo ==========================================
echo   CAP NHAT GIA PHA HO PHAM DINH
echo ==========================================

REM ---- 0. Kiem tra dau vao ----
if "%~1"=="" (
    echo.
    echo  Cach dung:
    echo    - Keo tha file .ged vao capnhat.bat
    echo    - Hoac go:  capnhat.bat ten-file.ged
    echo.
    pause
    exit /b 1
)

set "NGUON=%~1"

if not exist "%NGUON%" (
    echo.
    echo  [LOI] Khong thay file: %NGUON%
    echo.
    pause
    exit /b 1
)

if not exist "convert.py" (
    echo.
    echo  [LOI] Khong thay convert.py
    echo  Dat capnhat.bat cung thu muc voi convert.py
    echo.
    pause
    exit /b 1
)

if not exist "kiemtra.py" (
    echo.
    echo  [LOI] Khong thay kiemtra.py
    echo.
    pause
    exit /b 1
)

REM ---- Tim Python ----
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
    where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
    echo.
    echo  [LOI] Khong tim thay Python.
    echo.
    echo  Cai Python tai: https://www.python.org/downloads/
    echo  QUAN TRONG: luc cai NHO TICK "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [LOI] Khong tim thay Git.
    echo  Cai Git tai: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

REM ---- 1. Sao luu ban cu ----
echo.
echo  [1/4] Sao luu ban hien tai...

if not exist ".saoluu" mkdir ".saoluu"

set "DAU=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "DAU=!DAU: =0!"

if exist "data.json"  copy /y "data.json"  ".saoluu\data.json.!DAU!"  >nul
if exist "giapha.ged" copy /y "giapha.ged" ".saoluu\giapha.ged.!DAU!" >nul

echo        Da luu vao .saoluu\

set "CU=0"
if exist "data.json" (
    for /f %%n in ('%PY% -c "import json;print(json.load(open('data.json',encoding='utf-8'))['tong'])" 2^>nul') do set "CU=%%n"
)

REM ---- 2. Chuyen doi + loc ----
echo.
echo  [2/4] Chuyen doi va loc du lieu...
echo.

%PY% convert.py "%NGUON%" data.json
if errorlevel 1 (
    echo.
    echo  [LOI] convert.py that bai - KHONG doi gi ca.
    echo  Ban cu van con nguyen.
    echo.
    pause
    exit /b 1
)

REM ---- 3. Kiem tra an toan ----
echo.
echo  [3/4] Kiem tra an toan...
echo.

%PY% kiemtra.py
if errorlevel 1 (
    echo.
    echo  ==========================================
    echo   KIEM TRA THAT BAI - KHONG PUSH
    echo  ==========================================
    echo.
    echo  Ban cu van con trong .saoluu\
    echo.
    pause
    exit /b 1
)

set "MOI=0"
for /f %%n in ('%PY% -c "import json;print(json.load(open('data.json',encoding='utf-8'))['tong'])"') do set "MOI=%%n"

echo.
echo        So nguoi:  !CU!  --^>  !MOI!

if !CU! GTR 0 (
    set /a GIAM=!CU!-!MOI!
    if !GIAM! GTR 10 (
        echo.
        echo  [CANH BAO] Giam !GIAM! nguoi so voi ban cu - BAT THUONG.
        echo  Kiem tra ky. File cu van o .saoluu\
        echo.
        set "TRA="
        set /p "TRA=  Van tiep tuc? (go co de tiep): "
        if /i not "!TRA!"=="co" (
            echo.
            echo  Da huy. Khong push gi ca.
            pause
            exit /b 0
        )
    )
)

REM ---- 4. Push len GitHub ----
echo.
echo  [4/4] Day len GitHub...

git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [LOI] Thu muc nay chua noi voi GitHub.
    echo.
    echo  Chay ketnoi-github.bat truoc ^(chi can 1 lan^).
    echo.
    pause
    exit /b 1
)

git diff --quiet -- data.json giapha.ged 2>nul
if not errorlevel 1 (
    echo.
    echo        Du lieu khong doi - khong can push.
    echo.
    pause
    exit /b 0
)

echo.
echo        Thay doi:
git diff --stat -- data.json giapha.ged

echo.
set "TRA="
set /p "TRA=  Day len GitHub? (Enter = co, go k = khong): "
if /i "!TRA!"=="k" (
    echo.
    echo  Da huy. File moi van nam tren may, chua push.
    pause
    exit /b 0
)

git add data.json giapha.ged
git commit -q -m "Cap nhat gia pha - !MOI! nguoi"
git push

if errorlevel 1 (
    echo.
    echo  [LOI] Push that bai. Kiem tra mang / dang nhap GitHub.
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   XONG. Trang cap nhat sau 1-2 phut.
echo   https://hungps2.github.io/giapha/
echo ==========================================
echo.
pause
