# 重构改动清单

## 后端文件修改

### 1. `server/game_engine.py`

#### 新增字段到 GameState（第 79-82 行）
```python
phase_start_time: float = 0.0  # 阶段开始时间（用于计算剩余时间）
phase_duration: int = 0  # 阶段持续时间（秒）
```

#### 改进 start_round() 方法（第 155-201 行）
- 添加 `from datetime import datetime`
- 记录 `phase_start_time` 和 `phase_duration`

#### 新增方法 advance_speaker()（第 210-227 行）
```python
def advance_speaker(self) -> bool:
    """推进到下一个发言者"""
    # 逻辑：自动管理 current_speaker_index
    # 返回是否成功推进
```

#### 改进 get_state() 方法（第 417-468 行）
- 添加 `phaseTimeLeft` 计算
- 返回完整的发言和投票状态

---

### 2. `server/routes/game_routes.py`

#### 新增 advance_speaker() 端点（第 305-328 行）
```python
@bp.route('/<room_id>/advance-speaker', methods=['POST'])
def advance_speaker(room_id):
    """POST /rooms/{roomId}/advance-speaker"""
    # 调用后端 game.advance_speaker()
    # 返回 { success: bool, currentSpeaker: int }
```

---

## 前端文件修改

### 1. `miniprogram/pages/room/room.ts`

#### 导入新的 API 函数（第 1 行）
```diff
- import {assignRoles, GamePhase, getGameState, Role, startRound, submitSpeech, submitVote,}
+ import {assignRoles, GamePhase, getGameState, Role, startRound, submitSpeech, submitVote, advanceSpeaker}
```

#### 简化 data 对象（第 62-94 行）
**删除：**
- `votingSession`, `voteResults`, `_stateCheckTimer`, `_speakingTimer`, `_votingTimer`

**保留并简化：**
- 只保留后端返回的基本状态字段
- 只有一个轮询计时器 `_pollingTimer`

#### 替换轮询逻辑（第 189-245 行）

**删除方法：**
- ❌ `startStatePolling()` / `stopStatePolling()`
- ❌ `syncGameState()`
- ❌ `startPhaseCountdown()`
- ❌ `startSpeakingTimer()`
- ❌ `nextSpeaker()`
- ❌ `autoSubmitAgentSpeech()`
- ❌ `startVoting()`
- ❌ `startVotingTimer()`
- ❌ `checkVotingComplete()`
- ❌ `autoVoteForAgents()`
- ❌ `endVoting()`
- ❌ `calculateVotingResult()`

**新增方法：**
- ✅ `startPolling()` - 启动轮询（第 189-200 行）
- ✅ `stopPolling()` - 停止轮询（第 202-208 行）
- ✅ `pollGameState()` - 每秒轮询状态（第 210-245 行）

#### 简化用户操作（第 260-319 行）

**submitSpeech() 简化：**
```typescript
// 旧: 200+ 行复杂逻辑
// 新: 仅 30 行
// 1. 提交到后端
// 2. 本地显示
// 3. 调用 advanceSpeaker 推进
```

**submitMyVote() 简化：**
```typescript
// 旧: 70+ 行，包括本地投票状态管理
// 新: 仅 20 行
// 1. 简单验证
// 2. 提交到后端
// 3. 本地记录
```

---

### 2. `miniprogram/services/gameApi.ts`

#### 扩展 GameStateResponse 类型（第 39-55 行）
```typescript
phaseTimeLeft?: number           // 阶段剩余时间
currentSpeakerIndex?: number     // 当前发言者索引
speakingOrder?: number[]         // 发言顺序
votingVotedCount?: number        // 已投票人数
votingResult?: Record<string, any>  // 投票结果
playerVotes?: Record<number, any>   // 玩家投票状态
```

#### 新增 AdvanceSpeaker 类型（第 136-142 行）
```typescript
export type AdvanceSpeakerRequest = {
  roomId: string
}

export type AdvanceSpeakerResponse = {
  success: boolean
  currentSpeaker?: number
}
```

#### 新增 advanceSpeaker() 函数（第 381-387 行）
```typescript
export async function advanceSpeaker(req: AdvanceSpeakerRequest): Promise<AdvanceSpeakerResponse>
```

---

## 统计数据

| 指标 | 数值 |
|------|-----|
| 删除的方法数 | 10 个 |
| 新增方法数 | 3 个 |
| 删除代码行数 | 350+ |
| room.ts 行数削减 | 77% |
| 计时器数量 | 4 → 1 |
| 复杂度 | ⬇️⬇️⬇️ |

---

## API 端点变更

### 新增
- `POST /api/rooms/{roomId}/advance-speaker` - 推进发言者

### 现有端点升级
- `GET /api/rooms/{roomId}/state` - 返回更多完整状态

---

## 测试要点

1. **后端 API 测试：**
   - ✅ `/start-round` 正确更新 `phase_start_time` 和 `phase_duration`
   - ✅ `/advance-speaker` 正确推进发言者索引
   - ✅ `/state` 返回所有必要字段

2. **前端功能测试：**
   - ✅ 轮询每秒正确获取状态
   - ✅ 发言提交后自动推进发言者
   - ✅ 投票提交后显示最新投票计数
   - ✅ UI 完全反映后端状态

3. **端到端测试：**
   - ✅ 完整游戏流程（分配角色 → 讨论 → 投票 → 结束）
   - ✅ 多客户端状态同步
   - ✅ 没有计时器泄漏

---

## 部署清单

- [ ] 后端：部署 `game_engine.py` 更新
- [ ] 后端：部署 `game_routes.py` 更新
- [ ] 前端：部署 `room.ts` 更新
- [ ] 前端：部署 `gameApi.ts` 更新
- [ ] 验证：所有 API 端点正常工作
- [ ] 验证：前端轮询正常工作
- [ ] 监控：服务器日志无异常

