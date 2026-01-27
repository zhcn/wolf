# 狼人杀游戏后端服务

基于 Python Flask 的狼人杀游戏后端服务，提供完整的游戏逻辑和 API 接口。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

### 3. 运行服务

```bash
python app.py
```

服务默认运行在 `http://localhost:5000`

## 📋 项目结构

```
server/
├── app.py                 # Flask 主应用
├── game_engine.py         # 游戏引擎（核心逻辑）
├── routes/
│   ├── __init__.py
│   └── game_routes.py     # API 路由
├── requirements.txt       # 依赖列表
├── .env.example           # 环境配置示例
└── README.md              # 本文件
```

## 🎮 游戏引擎

### GameEngine 类

核心游戏逻辑引擎，处理：
- ✅ 角色分配
- ✅ 游戏阶段流转
- ✅ 投票逻辑
- ✅ 晚上行动
- ✅ 胜负判定

### 游戏阶段

```
waiting → role_assigned → day_discussion → day_voting → night_action → game_over
```

### 角色配置（12人局）

- 2 个狼人 (Werewolf)
- 1 个预言家 (Seer)
- 1 个女巫 (Witch)
- 1 个猎人 (Hunter)
- 6 个村民 (Villager)

## 🔌 API 接口

### 1. 分配角色

**端点**: `POST /api/rooms/{roomId}/assign-roles`

**请求**:
```json
{
  "seatCount": 12,
  "userSeat": 1
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Roles assigned successfully",
  "data": {
    "roomId": "classic",
    "rolesBySeat": {
      "1": "werewolf",
      "2": "seer",
      "3": "villager",
      ...
    }
  }
}
```

### 2. 获取游戏状态

**端点**: `GET /api/rooms/{roomId}/state`

**响应**:
```json
{
  "code": 200,
  "message": "Game state retrieved successfully",
  "data": {
    "room_id": "classic",
    "phase": "day_discussion",
    "result": "ongoing",
    "round": 1,
    "alive_players": [1, 2, 3, 4, 5],
    "dead_players": []
  }
}
```

### 3. 开始新阶段

**端点**: `POST /api/rooms/{roomId}/start-round`

**响应**:
```json
{
  "code": 200,
  "message": "Round started successfully",
  "data": {
    "phase": "day_discussion",
    "durationSeconds": 120
  }
}
```

### 4. 提交发言

**端点**: `POST /api/rooms/{roomId}/speech`

**请求**:
```json
{
  "seat": 1,
  "text": "我认为3号是狼人..."
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Speech submitted successfully",
  "data": {
    "success": true,
    "seat": 1
  }
}
```

### 5. 提交投票

**端点**: `POST /api/rooms/{roomId}/vote`

**请求**:
```json
{
  "voterSeat": 1,
  "targetSeat": 3
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Vote submitted successfully",
  "data": {
    "success": true,
    "voterSeat": 1,
    "targetSeat": 3
  }
}
```

### 6. 提交晚上行动

**端点**: `POST /api/rooms/{roomId}/night-action`

**请求** (狼人杀人):
```json
{
  "playerSeat": 1,
  "role": "werewolf",
  "actionType": "kill",
  "targetSeat": 5
}
```

**请求** (预言家检查):
```json
{
  "playerSeat": 2,
  "role": "seer",
  "actionType": "check",
  "targetSeat": 3
}
```

**请求** (女巫救人):
```json
{
  "playerSeat": 3,
  "role": "witch",
  "actionType": "save",
  "targetSeat": 5
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Night action submitted successfully",
  "data": {
    "success": true,
    "action": "kill",
    "result": "Action completed successfully"
  }
}
```

### 7. 获取游戏消息

**端点**: `GET /api/rooms/{roomId}/messages?after={lastMessageId}`

**响应**:
```json
{
  "code": 200,
  "message": "Messages retrieved successfully",
  "data": {
    "messages": [
      {
        "id": "1234567890",
        "timestamp": 1234567890.123,
        "type": "phase_change",
        "content": {
          "from": "role_assigned",
          "to": "day_discussion",
          "round": 1
        }
      },
      {
        "id": "1234567891",
        "timestamp": 1234567891.456,
        "type": "player_death",
        "content": {
          "seat": 5,
          "role": "villager",
          "killed_by": "werewolf",
          "round": 1
        }
      }
    ]
  }
}
```

## 🧪 测试

### 使用 curl 测试

```bash
# 分配角色
curl -X POST http://localhost:5000/api/rooms/classic/assign-roles \
  -H "Content-Type: application/json" \
  -d '{"seatCount": 12, "userSeat": 1}'

# 获取游戏状态
curl http://localhost:5000/api/rooms/classic/state

# 开始新阶段
curl -X POST http://localhost:5000/api/rooms/classic/start-round

# 提交投票
curl -X POST http://localhost:5000/api/rooms/classic/vote \
  -H "Content-Type: application/json" \
  -d '{"voterSeat": 1, "targetSeat": 3}'
```

### 使用 Python 测试

```python
import requests

BASE_URL = "http://localhost:5000/api"
room_id = "classic"

# 分配角色
resp = requests.post(f"{BASE_URL}/rooms/{room_id}/assign-roles", json={
    "seatCount": 12,
    "userSeat": 1
})
print(resp.json())

# 获取游戏状态
resp = requests.get(f"{BASE_URL}/rooms/{room_id}/state")
print(resp.json())

# 开始新阶段
resp = requests.post(f"{BASE_URL}/rooms/{room_id}/start-round")
print(resp.json())

# 提交投票
resp = requests.post(f"{BASE_URL}/rooms/{room_id}/vote", json={
    "voterSeat": 1,
    "targetSeat": 3
})
print(resp.json())
```

## 🔐 生产部署

### 使用 gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 使用 Docker

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

构建和运行:

```bash
docker build -t werewolf-game-backend .
docker run -p 5000:5000 werewolf-game-backend
```

## 📝 关键特性

- ✅ 完整的狼人杀游戏规则实现
- ✅ 多房间支持
- ✅ 实时游戏事件消息系统
- ✅ 灵活的角色配置
- ✅ RESTful API 设计
- ✅ 完善的错误处理

## 🔄 与前端集成

### 配置前端 API 地址

编辑 `miniprogram/config.ts`:

```typescript
export const BACKEND_BASE_URL = 'http://localhost:5000/api'
export const USE_MOCK_BACKEND = false  // 启用真实后端
```

## 📚 API 响应格式

所有 API 响应都遵循统一的格式:

```json
{
  "code": 200,              // HTTP 状态码
  "message": "Success",     // 消息说明
  "data": {}                // 响应数据
}
```

错误响应:

```json
{
  "code": 400,
  "message": "Bad Request",
  "data": null
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License

