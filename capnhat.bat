@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ==================================================================
REM  capnhat.bat - Loc du lieu gia pha tu file GEDCOM cua MyHeritage.
REM
REM  Usage: drag-drop the new .ged file onto this file.
REM
REM  Sinh ra HAI file da loc:
REM     data.json    - cho trang chinh
REM     giapha.ged   - cho nut "Xem so do cay" (Topola)
REM  Roi ban tu upload CA HAI len GitHub.
REM
REM  NOTE: This file must stay pure ASCII (no Vietnamese accents).
REM  Windows CMD reads .bat in a legacy codepage; UTF-8 accents get
REM  mangled and CMD tries to run the garbage as commands.
REM ==================================================================

echo.
echo ==========================================
echo   LOC DU LIEU GIA PHA HO PHAM DINH
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

REM ---- 1. Sao luu ban cu ----
echo.
echo  [1/3] Sao luu ban hien tai...

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
echo  [2/3] Chuyen doi va loc du lieu...
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
echo  [3/3] Kiem tra an toan...
echo.

%PY% kiemtra.py
if errorlevel 1 (
    echo.
    echo  ==========================================
    echo   KIEM TRA THAT BAI - DUNG UPLOAD!
    echo  ==========================================
    echo.
    echo  File vua sinh ra CO VAN DE. Dung dua len GitHub.
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
        echo  Kiem tra ky truoc khi upload. File cu van o .saoluu\
    )
)

REM ---- Xong ----
echo.
echo ==========================================
echo   XONG. Hai file da san sang:
echo.
echo      data.json     ^<- trang chinh
echo      giapha.ged    ^<- nut "Xem so do cay"
echo.
echo   UPLOAD CA HAI len GitHub repo giapha.
echo   ^(Github.com -^> repo giapha -^> Add file
echo    -^> Upload files -^> keo ca 2 file vao^)
echo.
echo   LUU Y: chi upload 2 file NAY.
echo   KHONG upload file .ged goc tu MyHeritage -
echo   ban goc con nguyen ngay/thang sinh nguoi
echo   con song, email, dia chi.
echo ==========================================
echo.

REM Mo thu muc de tien keo file len GitHub
set "MO="
set /p "MO=  Mo thu muc nay luon? (Enter = co, k = khong): "
if /i not "!MO!"=="k" start "" "%~dp0"

echo.
pause
