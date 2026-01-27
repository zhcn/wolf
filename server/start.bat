@echo off
REM 狼人杀游戏后端启动脚本 (Windows)

echo.
echo 🎮 狼人杀游戏后端服务
echo ======================================

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请从 https://www.python.org/downloads/ 下载安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 📦 安装依赖...
pip install -r requirements.txt -q

REM 创建 .env 文件
if not exist ".env" (
    echo ⚙️  创建 .env 配置文件...
    copy .env.example .env
)

REM 启动服务
echo.
echo 🚀 启动服务...
echo ======================================
echo.
python app.py

pause

