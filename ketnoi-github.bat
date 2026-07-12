@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ==================================================================
REM  ketnoi-github.bat - RUN ONCE
REM  Connects this folder to your GitHub repo.
REM  After this, just drag-drop a .ged file onto capnhat.bat
REM
REM  NOTE: This file must stay pure ASCII (no Vietnamese accents).
REM  Windows CMD reads .bat in a legacy codepage; UTF-8 accents get
REM  mangled and CMD tries to run the garbage as commands.
REM ==================================================================

echo.
echo ==========================================
echo   KET NOI THU MUC NAY VOI GITHUB
echo   (chi can chay MOT LAN)
echo ==========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo  [LOI] Khong tim thay Git.
    echo.
    echo  Cai Git tai: https://git-scm.com/download/win
    echo  Cai xong, mo lai cua so nay roi chay lai.
    echo.
    pause
    exit /b 1
)

REM ---- Neu da noi roi thi thoi ----
git remote get-url origin >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%u in ('git remote get-url origin') do set "CU=%%u"
    echo  Thu muc nay DA duoc noi voi:
    echo     !CU!
    echo.
    echo  Khong can lam gi nua.
    echo  Tu gio chi can keo tha file .ged vao capnhat.bat
    echo.
    pause
    exit /b 0
)

REM ---- Hoi dia chi repo ----
echo  Nhap dia chi repo GitHub cua ban.
echo  Vi du:  https://github.com/hungps2/giapha.git
echo.
echo  (Bo trong roi bam Enter de dung dia chi mac dinh o tren)
echo.

set "REPO="
set /p "REPO=  Dia chi repo: "
if "!REPO!"=="" set "REPO=https://github.com/hungps2/giapha.git"

echo.
echo  Se noi voi:  !REPO!
echo.
set "OK="
set /p "OK=  Dung khong? (Enter = dung, go k = huy): "
if /i "!OK!"=="k" (
    echo.
    echo  Da huy.
    pause
    exit /b 0
)

REM ---- 1. Khoi tao repo ----
echo.
echo  [1/5] Khoi tao repo git...
if exist ".git" (
    echo        Da co san .git - bo qua.
) else (
    git init -q
    if errorlevel 1 goto :LOI
    echo        Xong.
)

REM ---- 2. Danh tinh git ----
echo.
echo  [2/5] Kiem tra danh tinh git...

set "TEN="
set "MAIL="
for /f "delims=" %%a in ('git config user.name 2^>nul') do set "TEN=%%a"
for /f "delims=" %%a in ('git config user.email 2^>nul') do set "MAIL=%%a"

if "!TEN!"=="" (
    echo.
    set /p "TEN=  Ten cua ban: "
    git config user.name "!TEN!"
)
if "!MAIL!"=="" (
    set /p "MAIL=  Email GitHub cua ban: "
    git config user.email "!MAIL!"
)
echo        !TEN!  ^<!MAIL!^>

REM ---- 3. Noi voi GitHub ----
echo.
echo  [3/5] Noi voi GitHub...
git remote add origin "!REPO!"
if errorlevel 1 goto :LOI
git branch -M main
echo        Xong.

REM ---- 4. Keo lich su tu GitHub ve ----
echo.
echo  [4/5] Keo lich su tu GitHub ve...
echo        (lan dau se hien cua so dang nhap GitHub)
echo.

git fetch origin
if errorlevel 1 (
    echo.
    echo  [LOI] Khong keo duoc tu GitHub. Kiem tra:
    echo    - Dia chi repo dung chua?
    echo    - Repo da ton tai tren GitHub chua?
    echo    - Mang co on khong?
    echo.
    pause
    exit /b 1
)

git rev-parse --verify origin/main >nul 2>&1
if not errorlevel 1 (
    echo        Repo tren GitHub da co file san.
    echo        Giu nguyen file tren MAY, lay lich su tu GitHub.
    git reset --mixed origin/main
    if errorlevel 1 goto :LOI
) else (
    echo        Repo tren GitHub con rong - se day toan bo len.
)
echo        Xong.

REM ---- 5. Day len ----
echo.
echo  [5/5] Day file len GitHub...
echo.

git add .
git diff --cached --quiet
if not errorlevel 1 (
    echo        Khong co gi moi de day.
    goto :XONG
)

git commit -q -m "Cap nhat gia pha tu may"
git push -u origin main
if errorlevel 1 (
    echo.
    echo  [LOI] Push that bai.
    echo.
    echo  Neu bao 'rejected' hoac 'non-fast-forward', go 2 lenh nay:
    echo      git pull --rebase origin main
    echo      git push -u origin main
    echo.
    pause
    exit /b 1
)

:XONG
echo.
echo ==========================================
echo   XONG. Da noi voi GitHub.
echo.
echo   TU GIO moi lan cap nhat chi can:
echo   keo tha file .ged vao capnhat.bat
echo ==========================================
echo.
pause
exit /b 0

:LOI
echo.
echo  [LOI] Co loi xay ra. Xem thong bao o tren.
echo.
pause
exit /b 1
