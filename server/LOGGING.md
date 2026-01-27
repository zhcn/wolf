# 📋 日志系统说明

后端已配置完整的日志系统，记录所有 API 请求和响应。

## 📂 日志文件位置

```
server/
└── logs/
    └── app_YYYYMMDD.log  # 按日期自动生成
```

例如：`app_20240127.log`

## 📊 日志内容

### 1. 请求日志（Request）

每个 API 请求都会记录：
- ⏰ 时间戳
- 🌐 HTTP 方法 (GET/POST)
- 📍 请求路径
- 🔗 客户端 IP
- 📦 请求头 (Headers)
- 📄 请求体 (Request Body)

**示例**:
```
╔══════════════════════════════════════════════════════════════════════
║ 📨 API 请求
╠══════════════════════════════════════════════════════════════════════
║ 时间: 2024-01-27 10:30:45.123
║ 方法: POST
║ 路径: /api/rooms/classic/assign-roles
║ IP: 127.0.0.1
║ Headers: {...}
║ 请求体: {
║   "seatCount": 12,
║   "userSeat": 1
║ }
╚══════════════════════════════════════════════════════════════════════
```

### 2. 响应日志（Response）

每个 API 响应都会记录：
- ✅ HTTP 状态码
- ⏱️ 处理耗时（毫秒）
- 📤 Response Content-Type
- 📄 响应体 (Response Body)

**示例**:
```
╔══════════════════════════════════════════════════════════════════════
║ 📤 API 响应
╠══════════════════════════════════════════════════════════════════════
║ 状态码: 200 (INFO)
║ 耗时: 0.045s
║ Content-Type: application/json
║ 响应体: {
║   "code": 200,
║   "message": "Roles assigned successfully",
║   "data": {
║     "roomId": "classic",
║     "rolesBySeat": {...}
║   }
║ }
╚══════════════════════════════════════════════════════════════════════
```

### 3. 业务日志（Business Logic）

关键业务操作也会记录：
- 🎮 游戏初始化
- 🎭 角色分配
- 🔄 阶段流转
- 🗳️ 投票操作
- 💬 发言记录
- 🌙 晚上行动
- ✅ 成功操作
- ⚠️ 警告信息
- ❌ 错误信息

**示例**:
```
🎭 [assign_roles] 角色分配完成: {1: 'werewolf', 2: 'seer', ...}
🗳️ [vote] 房间: classic, 投票者: 1号, 目标: 3号
✅ [vote] 投票提交成功: 1号投票给3号
🌙 [night_action] 房间: classic, 玩家: 2号(seer), 行动: check, 目标: 3号
```

## 🔍 日志等级

| 等级 | 符号 | 说明 | 输出位置 |
|------|------|------|--------|
| DEBUG | 📝 | 详细调试信息 | 文件 + 控制台* |
| INFO | ℹ️ | 重要信息 | 文件 + 控制台 |
| WARNING | ⚠️ | 警告信息 | 文件 + 控制台 |
| ERROR | ❌ | 错误信息 | 文件 + 控制台 |

*DEBUG 级别只输出到文件，不显示在控制台

## 📖 查看日志

### 方法 1: 查看日志文件

```bash
# 查看今天的日志
cat logs/app_$(date +%Y%m%d).log

# 实时查看日志（类似 tail -f）
tail -f logs/app_$(date +%Y%m%d).log

# 搜索特定内容
grep "assign_roles" logs/app_$(date +%Y%m%d).log

# 查看错误
grep "❌" logs/app_$(date +%Y%m%d).log
```

### 方法 2: 控制台输出

启动后端时，会在控制台实时输出 INFO 以上等级的日志：

```bash
cd server
./start.sh
# 或
python app.py
```

控制台输出示例：
```
2024-01-27 10:30:45,123 - api - INFO - 🎮 [assign_roles] 房间: classic
2024-01-27 10:30:45,145 - api - INFO - 🎭 [assign_roles] 角色分配完成: {...}
2024-01-27 10:30:46,200 - api - INFO - 🗳️ [vote] 投票提交成功: 1号投票给3号
```

## 🔧 自定义日志

### 修改日志级别

编辑 `app.py` 中的日志配置：

```python
# DEBUG: 显示所有日志
console_handler.setLevel(logging.DEBUG)

# INFO: 只显示重要信息
console_handler.setLevel(logging.INFO)

# WARNING: 只显示警告和错误
console_handler.setLevel(logging.WARNING)
```

### 添加自定义日志

在 API 路由中：

```python
from flask import current_app
logger = current_app.logger

# 记录日志
logger.debug("调试信息")
logger.info("重要信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 📊 日志分析

### 查看平均响应时间

```bash
grep "耗时:" logs/app_*.log | awk -F': ' '{print $2}' | awk '{s+=$1; n++} END {print "平均耗时: " s/n "s"}'
```

### 查看错误频率

```bash
grep "❌" logs/app_*.log | wc -l
```

### 查看特定房间的日志

```bash
grep "classic" logs/app_*.log
```

### 查看某个时间段的日志

```bash
grep "2024-01-27 10:3" logs/app_*.log
```

## 📌 常见日志模式

### 成功的游戏流程

```
📨 API 请求: assign-roles
✅ 游戏实例创建成功
🎭 角色分配完成
📤 API 响应: 200

📨 API 请求: start-round
🔄 进入阶段 day_discussion
📤 API 响应: 200

📨 API 请求: vote
✅ 投票提交成功
📤 API 响应: 200
```

### 错误情况

```
📨 API 请求: vote
⚠️ 房间不存在: invalid_room
📤 API 响应: 404

📨 API 请求: night-action
⚠️ 行动无效: 2号的seer执行kill
📤 API 响应: 400
```

## 🚀 性能监控

从日志中可以监控：

1. **API 响应时间**
   ```
   耗时: 0.045s  ✅ 快速
   耗时: 0.500s  ⚠️ 稍慢
   耗时: 2.000s  ❌ 太慢
   ```

2. **错误率**
   - 统计 ❌ 的出现次数
   - 与总请求数对比

3. **特定操作耗时**
   - 角色分配
   - 投票统计
   - 晚上行动处理

## 💾 日志清理

日志文件会按日期自动分割（每天一个文件）。如需清理旧日志：

```bash
# 删除 7 天前的日志
find logs -name "app_*.log" -mtime +7 -delete

# 或手动删除
rm logs/app_20240120.log logs/app_20240121.log
```

## ⚙️ 配置文件位置

日志配置在 `app.py` 中的以下部分：

```python
# 第 25-50 行：日志配置
# - 日志目录创建
# - 日志格式设置
# - 文件处理器配置
# - 控制台处理器配置
```

## 📝 日志示例

完整的游戏过程日志示例：

```
2024-01-27 10:30:45,100 - api - INFO -
╔══════════════════════════════════════════════════════════════════════
║ 📨 API 请求
╠══════════════════════════════════════════════════════════════════════
║ 时间: 2024-01-27 10:30:45.100
║ 方法: POST
║ 路径: /api/rooms/classic/assign-roles
║ IP: 127.0.0.1
║ 请求体: {"seatCount": 12, "userSeat": 1}
╚══════════════════════════════════════════════════════════════════════

2024-01-27 10:30:45,120 - api - DEBUG - 🎮 [assign_roles] 房间: classic
2024-01-27 10:30:45,121 - api - DEBUG - 📝 [assign_roles] 座位数: 12
2024-01-27 10:30:45,122 - api - DEBUG - ✅ [assign_roles] 游戏实例创建/获取成功
2024-01-27 10:30:45,145 - api - INFO - 🎭 [assign_roles] 角色分配完成: {1: 'werewolf', 2: 'seer', ...}
2024-01-27 10:30:45,146 - api - DEBUG - 📤 [assign_roles] 返回响应: {'roomId': 'classic', 'rolesBySeat': {...}}

2024-01-27 10:30:45,150 - api - INFO -
╔══════════════════════════════════════════════════════════════════════
║ 📤 API 响应
╠══════════════════════════════════════════════════════════════════════
║ 状态码: 200 (INFO)
║ 耗时: 0.050s
║ Content-Type: application/json
║ 响应体: {"code": 200, "message": "Roles assigned successfully", "data": {...}}
╚══════════════════════════════════════════════════════════════════════
```

## 🎯 调试技巧

### 1. 追踪特定房间
```bash
grep "classic" logs/app_*.log
```

### 2. 查看特定玩家的操作
```bash
grep "1号\|2号\|3号" logs/app_*.log
```

### 3. 查看所有错误
```bash
grep "❌\|ERROR" logs/app_*.log
```

### 4. 查看长耗时的请求
```bash
grep "耗时: [1-9]" logs/app_*.log  # 1秒以上的请求
```

---

**日志系统已完全配置！所有 API 请求/响应都会被记录。** 🎉

