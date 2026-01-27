#!/bin/bash

# 狼人杀游戏后端启动脚本

echo "🎮 狼人杀游戏后端服务"
echo "======================================"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    exit 1
fi

## 检查依赖
#if [ ! -d "venv" ]; then
#    echo "📦 创建虚拟环境..."
#    python3 -m venv venv
#fi
#
## 激活虚拟环境
#echo "🔄 激活虚拟环境..."
#source venv/bin/activate
#
## 安装依赖
#echo "📦 安装依赖..."
#pip install -r requirements.txt -q
#
## 创建 .env 文件（如果不存在）
#if [ ! -f ".env" ]; then
#    echo "⚙️  创建 .env 配置文件..."
#    cp .env.example .env
#fi

# 启动服务
echo ""
echo "🚀 启动服务..."
echo "======================================"
python app.py

