# 🎮 狼人杀游戏后端设置指南

完整的 Python Flask 后端实现已经完成！这是一份快速设置和运行指南。

## 📦 后端项目结构

```
server/
├── app.py                 # Flask 主应用入口
├── game_engine.py         # 游戏核心引擎（最重要的文件）
├── routes/
│   ├── __init__.py
│   └── game_routes.py     # API 路由定义
├── requirements.txt       # Python 依赖
├── .env                   # 环境配置
├── .env.example           # 环境配置示例
├── start.sh               # Linux/Mac 启动脚本
├── start.bat              # Windows 启动脚本
├── test_api.py            # API 测试脚本
└── README.md              # 详细文档
```

## 🚀 快速开始

### 方式 1: 使用启动脚本（推荐）

#### Mac/Linux:
```bash
cd server
chmod +x start.sh
./start.sh
```

#### Windows:
```bash
cd server
start.bat
```

### 方式 2: 手动启动

```bash
# 进入 server 目录
cd server

# 创建虚拟环境（首次）
python3 -m venv venv

# 激活虚拟环境
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

✅ 服务将运行在 `http://localhost:5000`

## 🧪 测试 API

### 方式 1: 使用测试脚本
```bash
cd server
python test_api.py
```

这会自动测试所有 API 接口。

### 方式 2: 使用 curl
```bash
# 分配角色
curl -X POST http://localhost:5000/api/rooms/classic/assign-roles \
  -H "Content-Type: application/json" \
  -d '{"seatCount": 12, "userSeat": 1}'

# 获取游戏状态
curl http://localhost:5000/api/rooms/classic/state

# 开始新阶段
curl -X POST http://localhost:5000/api/rooms/classic/start-round
```

### 方式 3: 使用 Postman/API 客户端
1. 打开 Postman
2. 导入以下请求（见下方完整 API 列表）
3. 测试每个端点

## 🔌 完整 API 参考

### 1. 分配角色
- **POST** `/api/rooms/{roomId}/assign-roles`
- 请求: `{ "seatCount": 12, "userSeat": 1 }`
- 返回: 座位到角色的映射

### 2. 获取游戏状态
- **GET** `/api/rooms/{roomId}/state`
- 返回: 当前游戏状态

### 3. 开始新阶段
- **POST** `/api/rooms/{roomId}/start-round`
- 返回: 下一个阶段和持续时间

### 4. 提交发言
- **POST** `/api/rooms/{roomId}/speech`
- 请求: `{ "seat": 1, "text": "..." }`

### 5. 提交投票
- **POST** `/api/rooms/{roomId}/vote`
- 请求: `{ "voterSeat": 1, "targetSeat": 3 }`

### 6. 晚上行动
- **POST** `/api/rooms/{roomId}/night-action`
- 请求: `{ "playerSeat": 1, "role": "werewolf", "actionType": "kill", "targetSeat": 5 }`

### 7. 获取消息
- **GET** `/api/rooms/{roomId}/messages`
- 支持长轮询: `?after={lastMessageId}`

详见 `server/README.md` 获取完整的 API 文档。

## ⚙️ 配置说明

### 环境变量 (.env)

```env
# 环境: development 或 production
FLASK_ENV=development

# 端口
PORT=5000

# 调试模式
DEBUG=True
```

### 前端配置 (miniprogram/config.ts)

已自动更新为:
```typescript
export const BACKEND_BASE_URL = 'http://localhost:5000/api'
export const USE_MOCK_BACKEND = false
```

如需改回 Mock 模式，修改为:
```typescript
export const USE_MOCK_BACKEND = true
```

## 🎮 游戏流程

### 游戏阶段顺序

```
1. 等待开始 (waiting)
2. 角色分配 (role_assigned)
3. 白天讨论 (day_discussion) - 玩家自由发言
4. 白天投票 (day_voting) - 玩家投票驱逐
5. 晚上行动 (night_action) - 狼人/预言家/女巫行动
6. 重复 3-5 直到游戏结束
7. 游戏结束 (game_over)
```

### 角色说明（12人局）

| 角色 | 数量 | 职能 |
|------|------|------|
| 狼人 | 2 | 晚上杀死一个村民 |
| 预言家 | 1 | 晚上检查一个玩家的身份 |
| 女巫 | 1 | 晚上可救人或毒人 |
| 猎人 | 1 | 被投票驱逐时可反杀一个 |
| 村民 | 6 | 没有特殊能力 |

### 胜利条件

- **村民胜利**: 所有狼人被驱逐或杀死
- **狼人胜利**: 狼人数 ≥ 村民数

## 🐛 常见问题

### Q1: 后端启动失败？

**检查列表**:
- ✅ 确保 Python 3.8+ 已安装: `python3 --version`
- ✅ 依赖已安装: `pip install -r requirements.txt`
- ✅ 端口 5000 未被占用
- ✅ 防火墙未阻止 5000 端口

**解决方案**:
```bash
# 切换到其他端口
export PORT=8000  # Mac/Linux
# 或编辑 .env 文件修改 PORT

python app.py
```

### Q2: 前端连接不上后端？

**检查**:
- ✅ 后端是否运行: `curl http://localhost:5000/api/rooms/test/health`
- ✅ CORS 是否配置正确
- ✅ `config.ts` 中 `USE_MOCK_BACKEND` 是否为 `false`
- ✅ `BACKEND_BASE_URL` 是否正确

### Q3: 游戏状态丢失？

游戏数据存储在内存中。如需持久化，可集成数据库：
- PostgreSQL / MySQL
- MongoDB
- Redis

### Q4: 如何在生产环境部署？

参考 `server/README.md` 中的"生产部署"章节，使用 Docker 或 Gunicorn。

## 📊 架构设计

### 核心模块

1. **app.py** - Flask 应用主入口
   - CORS 配置
   - 错误处理
   - 蓝图注册

2. **game_engine.py** - 游戏逻辑核心
   - GameEngine 类：游戏状态和规则
   - GameState 类：游戏快照
   - Role/GamePhase 枚举：类型定义
   - 功能: 角色分配、阶段流转、投票、胜负判定

3. **routes/game_routes.py** - API 路由
   - 7 个 API 端点
   - 请求验证和错误处理
   - 响应格式化

### 数据流

```
前端请求
  ↓
Flask 路由 (game_routes.py)
  ↓
游戏引擎 (game_engine.py)
  ↓
游戏状态 (GameState)
  ↓
响应数据返回前端
```

## 🔒 安全建议

- [ ] 生产环境启用 HTTPS
- [ ] 添加用户认证
- [ ] 实现 API 速率限制
- [ ] 添加输入验证
- [ ] 使用数据库替代内存存储
- [ ] 定期备份数据

## 📈 性能优化

- 目前支持无限数量的并发房间
- 内存使用随房间数量线性增长
- 建议生产环境使用数据库 + 缓存

## 🔗 相关资源

- Flask 官方文档: https://flask.palletsprojects.com
- Flask-CORS: https://flask-cors.readthedocs.io
- Python 虚拟环境: https://docs.python.org/3/tutorial/venv.html

## 📝 后续改进

- [ ] 添加数据库支持（PostgreSQL）
- [ ] WebSocket 实时推送
- [ ] 用户认证系统
- [ ] 游戏重放功能
- [ ] 战绩统计系统
- [ ] 管理后台
- [ ] API 文档 (Swagger)

## ✅ 完成清单

- ✅ 完整的游戏规则实现
- ✅ 7 个核心 API 接口
- ✅ Mock 数据支持
- ✅ 多房间并发支持
- ✅ 详细的 API 文档
- ✅ 测试脚本
- ✅ 启动脚本（Mac/Linux/Windows）
- ✅ 前端配置更新
- ✅ 错误处理
- ✅ CORS 支持

现在你可以：
1. ✅ 运行后端服务
2. ✅ 测试 API 接口
3. ✅ 前端连接后端
4. ✅ 完整的狼人杀游戏！

祝你游戏愉快！🎮

