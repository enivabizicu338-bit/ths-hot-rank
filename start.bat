@echo off
chcp 65001 >nul
echo ========================================
echo   同花顺热榜 - 本地Web服务
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未安装Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 检查依赖...
pip install flask flask-cors requests -q

REM 启动服务
echo [2/3] 启动Web服务...
echo.
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务
echo.

python app.py

pause