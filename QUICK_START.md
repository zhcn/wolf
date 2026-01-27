# ⚡ 快速开始指南

## 🎯 30秒快速启动

### 后端（Python）

```bash
cd server
# Mac/Linux
chmod +x start.sh && ./start.sh
# Windows
start.bat
```

✅ 服务启动在 `http://localhost:5000`

### 前端（微信小程序）

```bash
# 微信开发者工具中
1. 打开项目
2. 点击 "编译"
3. 点击 "预览" 在手机上查看
```

### 测试 API

```bash
cd server
python test_api.py
```

---

## 📱 游戏流程

```
1. 启动后端
2. 启动前端/编译预览
3. 点击"开始游戏"
4. 等待角色分配
5. 白天讨论 → 发言
6. 白天投票 → 投票
7. 晚上行动 → 特殊角色操作
8. 重复 5-7 直到游戏结束
```

---

## 🔧 配置修改

### 使用本地后端
```typescript
// miniprogram/config.ts
export const BACKEND_BASE_URL = 'http://localhost:5000/api'
export const USE_MOCK_BACKEND = false
```

### 切换到 Mock 模式（不需要后端）
```typescript
export const USE_MOCK_BACKEND = true
```

---

## 🐛 故障排除

| 问题 | 解决方案 |
|------|--------|
| 后端启动失败 | 检查 Python 版本: `python3 --version` |
| 端口被占用 | 修改 `.env` 中的 `PORT` |
| 前端连接失败 | 检查 `config.ts` 中的 URL 配置 |
| 游戏卡住 | 清除本地存储重试 |

---

## 📂 重要文件

| 文件 | 说明 |
|------|------|
| `server/app.py` | 后端入口 |
| `server/game_engine.py` | 游戏逻辑核心 |
| `miniprogram/config.ts` | 前端配置 |
| `miniprogram/pages/room/room.ts` | 房间页面逻辑 |
| `miniprogram/services/gameApi.ts` | API 服务 |

---

## 🚀 常用命令

```bash
# 后端
cd server
python app.py                    # 启动服务
python test_api.py               # 测试 API
pip install -r requirements.txt  # 安装依赖

# 前端
npm install                      # 安装依赖
```

---

## 🎮 游戏角色

- 🐺 **狼人** (2人) - 晚上杀人
- 🔮 **预言家** (1人) - 晚上检查
- 🧪 **女巫** (1人) - 晚上救人/毒人
- 🏹 **猎人** (1人) - 被投票时反杀
- 👨 **村民** (6人) - 无特殊能力

---

## 📊 API 快速参考

```bash
# 分配角色
curl -X POST http://localhost:5000/api/rooms/classic/assign-roles \
  -H "Content-Type: application/json" \
  -d '{"seatCount": 12, "userSeat": 1}'

# 获取状态
curl http://localhost:5000/api/rooms/classic/state

# 开始新阶段
curl -X POST http://localhost:5000/api/rooms/classic/start-round

# 投票
curl -X POST http://localhost:5000/api/rooms/classic/vote \
  -H "Content-Type: application/json" \
  -d '{"voterSeat": 1, "targetSeat": 3}'
```

---

## 📚 完整文档

- `PROJECT_SUMMARY.md` - 项目完整说明
- `BACKEND_SETUP.md` - 后端详细设置
- `server/README.md` - 后端 API 文档

---

## ✨ 特色功能

✅ 完整的游戏规则
✅ 多阶段 UI 交互
✅ 实时倒计时显示
✅ 自动游戏循环
✅ 平滑动画效果
✅ 三列响应式布局

---

**🎮 现在就开始游戏吧！**

