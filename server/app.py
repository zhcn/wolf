"""
狼人杀游戏后端服务
用于处理游戏逻辑、玩家管理、角色分配等
"""
import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, g
from flask_cors import CORS

# 加载环境变量
load_dotenv()

# 创建 Flask 应用
app = Flask(__name__)

# 配置 CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ============== 日志配置 ==============

# 创建日志目录
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志格式
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')

# 创建日志处理器
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format))

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# 配置应用日志
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)

# 创建专用的 API 日志记录器
api_logger = logging.getLogger('api')
api_logger.setLevel(logging.DEBUG)
api_logger.addHandler(file_handler)
api_logger.addHandler(console_handler)

# ============== 请求/响应日志中间件 ==============

@app.before_request
def log_request():
    """记录每个请求"""
    g.start_time = datetime.now()

    # 记录请求信息
    request_method = request.method
    request_path = request.path
    request_ip = request.remote_addr

    # 记录请求体
    request_data = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            request_data = request.get_json()
        else:
            request_data = request.get_data(as_text=True)

    api_logger.info(f"""
╔══════════════════════════════════════════════════════════════════════
║ 📨 API 请求
╠══════════════════════════════════════════════════════════════════════
║ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}
║ 方法: {request_method}
║ 路径: {request_path}
║ IP: {request_ip}
║ Headers: {dict(request.headers)}
║ 请求体: {json.dumps(request_data, indent=2, ensure_ascii=False) if request_data else 'None'}
╚══════════════════════════════════════════════════════════════════════
    """)

@app.after_request
def log_response(response):
    """记录每个响应"""
    duration = (datetime.now() - g.start_time).total_seconds()

    # 记录响应信息
    status_code = response.status_code
    content_type = response.content_type

    # 尝试解析响应体
    response_data = None
    if response.is_json:
        try:
            response_data = response.get_json()
        except:
            response_data = response.get_data(as_text=True)
    else:
        response_data = response.get_data(as_text=True)[:200]  # 限制长度

    # 根据状态码选择日志级别
    log_level = 'INFO' if status_code < 400 else 'WARNING' if status_code < 500 else 'ERROR'

    api_logger.info(f"""
╔══════════════════════════════════════════════════════════════════════
║ 📤 API 响应
╠══════════════════════════════════════════════════════════════════════
║ 状态码: {status_code} ({log_level})
║ 耗时: {duration:.3f}s
║ Content-Type: {content_type}
║ 响应体: {json.dumps(response_data, indent=2, ensure_ascii=False) if response_data else 'None'}
╚══════════════════════════════════════════════════════════════════════
    """)

    return response

# 导入蓝图
from routes import game_routes

# 注册蓝图
app.register_blueprint(game_routes.bp)

@app.errorhandler(404)
def not_found(error):
    """处理 404 错误"""
    return {
        'code': 404,
        'message': 'Not Found',
        'data': None
    }, 404

@app.errorhandler(500)
def server_error(error):
    """处理 500 错误"""
    return {
        'code': 500,
        'message': 'Internal Server Error',
        'data': None
    }, 500

if __name__ == '__main__':
    # 开发环境下运行
    debug = os.getenv('FLASK_ENV') == 'development'
    port = 5010 #int(os.getenv('PORT', 5010))
    app.logger.info(f'🚀 服务启动在 http://0.0.0.0:{port}')
    app.run(debug=debug, host='0.0.0.0', port=port)

