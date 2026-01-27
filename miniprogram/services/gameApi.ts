import {USE_MOCK_BACKEND} from '../config'
import {request} from '../utils/api'

export type Role =
  | 'werewolf'
  | 'villager'
  | 'seer'
  | 'witch'
  | 'hunter'

export type GamePhase =
  | 'waiting'        // 等待开始
  | 'role_assigned'  // 角色已分配
  | 'day_discussion' // 白天讨论
  | 'day_voting'     // 白天投票
  | 'night_action'   // 晚上行动（狼人/预言家/女巫）
  | 'day_result'     // 白天投票结果
  | 'night_result'   // 晚上行动结果
  | 'game_over'      // 游戏结束

export type GameResult = 'werewolf_win' | 'villager_win' | 'ongoing'

export type AssignRolesRequest = {
  roomId: string
  seatCount: number
  userSeat: number
}

export type AssignRolesResponse = {
  roomId: string
  rolesBySeat: Record<number, Role>
}

// 获取游戏状态
export type GameStateRequest = {
  roomId: string
}

export type GameStateResponse = {
  roomId: string
  phase: GamePhase
  result: GameResult
  round: number                    // 当前轮数
  alivePlayers: number[]            // 存活玩家座位号
  deadPlayers: number[]             // 死亡玩家座位号
  currentSpeaker?: number          // 当前发言者座位号
  speakingTimeLeft?: number        // 发言剩余时间（秒）
  votingTimeLeft?: number          // 投票剩余时间（秒）
  nightActionTimeLeft?: number     // 晚上行动剩余时间（秒）
  lastDeadPlayer?: {
    seat: number
    role: Role
    killedBy: 'vote' | 'werewolf' | 'witch'
  }
}

// 开始新一轮游戏
export type StartRoundRequest = {
  roomId: string
}

export type StartRoundResponse = {
  phase: GamePhase
  durationSeconds: number
}

// 提交发言
export type SubmitSpeechRequest = {
  roomId: string
  seat: number
  text: string
}

export type SubmitSpeechResponse = {
  success: boolean
  nextPhase?: GamePhase
}

// 投票
export type SubmitVoteRequest = {
  roomId: string
  voterSeat: number
  targetSeat: number
}

export type SubmitVoteResponse = {
  success: boolean
  votedOut?: number  // 被投票出局的玩家座位号
}

// 晚上行动（狼人/预言家/女巫）
export type SubmitNightActionRequest = {
  roomId: string
  playerSeat: number
  role: Role
  actionType: 'kill' | 'check' | 'save'
  targetSeat?: number
}

export type SubmitNightActionResponse = {
  success: boolean
  result?: {
    action: string
    result: string
  }
}

// 获取游戏消息（用于长轮询）
export type GetGameMessagesRequest = {
  roomId: string
  lastMessageId?: string
}

export type GameMessage = {
  id: string
  timestamp: number
  type: 'phase_change' | 'player_death' | 'vote_result' | 'day_result' | 'game_end'
  content: unknown
}

export type GetGameMessagesResponse = {
  messages: GameMessage[]
}

// 获取 Agent 发言
export type GetAgentSpeechRequest = {
  roomId: string
  seat: number  // Agent 的座位号
}

export type GetAgentSpeechResponse = {
  seat: number
  text: string  // Agent 生成的发言内容
}

// 获取 Agent 晚上行动
export type GetAgentActionRequest = {
  roomId: string
  seat: number  // Agent 的座位号
  role: Role
  availableTargets: number[]  // 可选的目标列表
}

export type GetAgentActionResponse = {
  seat: number
  actionType: 'kill' | 'check' | 'save'
  targetSeat?: number
}

const ROLE_POOL: Role[] = ['werewolf', 'werewolf', 'seer', 'witch', 'hunter', 'villager', 'villager', 'villager', 'villager', 'villager', 'villager', 'villager']

// 游戏状态缓存（仅用于 mock）
const mockGameStates: Map<string, GameStateResponse & { rolesBySeat: Record<number, Role> }> = new Map()

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const tmp = a[i]
    a[i] = a[j]
    a[j] = tmp
  }
  return a
}

function mockAssignRoles(req: AssignRolesRequest): AssignRolesResponse {
  const seats = Array.from({ length: req.seatCount }, (_, idx) => idx + 1)
  const pool = req.seatCount === 12 ? ROLE_POOL : shuffle(ROLE_POOL).slice(0, req.seatCount)
  const shuffled = shuffle(pool)
  const rolesBySeat: Record<number, Role> = {}
  seats.forEach((seat, idx) => {
    rolesBySeat[seat] = shuffled[idx] ?? 'villager'
  })

  // 初始化游戏状态
  mockGameStates.set(req.roomId, {
    roomId: req.roomId,
    phase: 'role_assigned',
    result: 'ongoing',
    round: 1,
    alivePlayers: seats,
    deadPlayers: [],
    rolesBySeat,
    currentSpeaker: 1,
    speakingTimeLeft: 60,
  })

  return { roomId: req.roomId, rolesBySeat }
}

function mockGetGameState(req: GameStateRequest): GameStateResponse {
  const state = mockGameStates.get(req.roomId)
  if (!state) {
    return {
      roomId: req.roomId,
      phase: 'waiting',
      result: 'ongoing',
      round: 0,
      alivePlayers: [],
      deadPlayers: [],
    }
  }
  const { rolesBySeat, ...gameState } = state
  return gameState
}

function mockStartRound(req: StartRoundRequest): StartRoundResponse {
  const state = mockGameStates.get(req.roomId)
  if (!state) {
    return { phase: 'waiting', durationSeconds: 0 }
  }

  // 模拟游戏阶段流转
  let nextPhase: GamePhase
  let durationSeconds: number

  if (state.phase === 'role_assigned') {
    nextPhase = 'day_discussion'
    durationSeconds = 120  // 白天讨论 2 分钟
  } else if (state.phase === 'day_discussion') {
    nextPhase = 'day_voting'
    durationSeconds = 60   // 白天投票 1 分钟
  } else if (state.phase === 'day_voting') {
    nextPhase = 'night_action'
    durationSeconds = 120  // 晚上行动 2 分钟
  } else if (state.phase === 'night_action') {
    nextPhase = 'day_discussion'
    durationSeconds = 120
    state.round++
  } else {
    nextPhase = 'waiting'
    durationSeconds = 0
  }

  state.phase = nextPhase
  return { phase: nextPhase, durationSeconds }
}

function mockSubmitSpeech(req: SubmitSpeechRequest): SubmitSpeechResponse {
  return { success: true }
}

function mockSubmitVote(req: SubmitVoteRequest): SubmitVoteResponse {
  const state = mockGameStates.get(req.roomId)
  if (!state) {
    return { success: false }
  }

  // 模拟随机投票结果
  const votedOut = state.alivePlayers[Math.floor(Math.random() * state.alivePlayers.length)]
  return { success: true, votedOut }
}

function mockSubmitNightAction(req: SubmitNightActionRequest): SubmitNightActionResponse {
  return { success: true }
}

function mockGetGameMessages(req: GetGameMessagesRequest): GetGameMessagesResponse {
  return { messages: [] }
}

function mockGetAgentSpeech(req: GetAgentSpeechRequest): GetAgentSpeechResponse {
  // 模拟 Agent 发言
  const speeches = [
    '我觉得这一轮大家都表现得很不错。',
    '我注意到有些人的发言方式有点可疑。',
    '让我们冷静下来，好好分析一下情况。',
    '根据今天的讨论，我认为需要投票驱逐某个人。',
    '大家要相信彼此，团结起来对抗狼人。',
    '我的直觉告诉我这个人可能有问题。',
    '让我们投票吧，不要浪费时间。',
    '我赞同刚才的分析，非常有道理。',
  ]
  return {
    seat: req.seat,
    text: speeches[Math.floor(Math.random() * speeches.length)],
  }
}

function mockGetAgentAction(req: GetAgentActionRequest): GetAgentActionResponse {
  // 模拟 Agent 晚上行动
  const targetSeat = req.availableTargets[Math.floor(Math.random() * req.availableTargets.length)]

  let actionType: 'kill' | 'check' | 'save'
  if (req.role === 'werewolf') {
    actionType = 'kill'
  } else if (req.role === 'seer') {
    actionType = 'check'
  } else if (req.role === 'witch') {
    actionType = Math.random() > 0.5 ? 'save' : 'save'  // 女巫可以救人
  } else {
    actionType = 'kill'  // 默认
  }

  return {
    seat: req.seat,
    actionType,
    targetSeat,
  }
}

// ============== 实际 API 调用 ==============

export async function assignRoles(req: AssignRolesRequest): Promise<AssignRolesResponse> {
  if (USE_MOCK_BACKEND) return mockAssignRoles(req)
  return await request<AssignRolesResponse, AssignRolesRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/assign-roles`,
    data: req,
  })
}

export async function getGameState(req: GameStateRequest): Promise<GameStateResponse> {
  if (USE_MOCK_BACKEND) return mockGetGameState(req)
  return await request<GameStateResponse, GameStateRequest>({
    method: 'GET',
    path: `/rooms/${encodeURIComponent(req.roomId)}/state`,
  })
}

export async function startRound(req: StartRoundRequest): Promise<StartRoundResponse> {
  if (USE_MOCK_BACKEND) return mockStartRound(req)
  return await request<StartRoundResponse, StartRoundRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/start-round`,
    data: req,
  })
}

export async function submitSpeech(req: SubmitSpeechRequest): Promise<SubmitSpeechResponse> {
  if (USE_MOCK_BACKEND) return mockSubmitSpeech(req)
  return await request<SubmitSpeechResponse, SubmitSpeechRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/speech`,
    data: req,
  })
}

export async function submitVote(req: SubmitVoteRequest): Promise<SubmitVoteResponse> {
  if (USE_MOCK_BACKEND) return mockSubmitVote(req)
  return await request<SubmitVoteResponse, SubmitVoteRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/vote`,
    data: req,
  })
}

export async function submitNightAction(req: SubmitNightActionRequest): Promise<SubmitNightActionResponse> {
  if (USE_MOCK_BACKEND) return mockSubmitNightAction(req)
  return await request<SubmitNightActionResponse, SubmitNightActionRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/night-action`,
    data: req,
  })
}

export async function getGameMessages(req: GetGameMessagesRequest): Promise<GetGameMessagesResponse> {
  if (USE_MOCK_BACKEND) return mockGetGameMessages(req)
  return await request<GetGameMessagesResponse, GetGameMessagesRequest>({
    method: 'GET',
    path: `/rooms/${encodeURIComponent(req.roomId)}/messages${req.lastMessageId ? `?after=${req.lastMessageId}` : ''}`,
  })
}

export async function getAgentSpeech(req: GetAgentSpeechRequest): Promise<GetAgentSpeechResponse> {
  if (USE_MOCK_BACKEND) return mockGetAgentSpeech(req)
  return await request<GetAgentSpeechResponse, GetAgentSpeechRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/agent-speech`,
    data: req,
  })
}

export async function getAgentAction(req: GetAgentActionRequest): Promise<GetAgentActionResponse> {
  if (USE_MOCK_BACKEND) return mockGetAgentAction(req)
  return await request<GetAgentActionResponse, GetAgentActionRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/agent-action`,
    data: req,
  })
}

