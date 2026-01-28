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
  | 'announcing'     // 主持人播报阶段
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
  phaseTimeLeft?: number           // 阶段剩余时间（秒）
  currentSpeaker?: number          // 当前发言者座位号
  currentSpeakerIndex?: number     // 当前发言者索引
  speakingOrder?: number[]         // 发言顺序
  speakingTimeLeft?: number        // 发言剩余时间（秒）
  votingTimeLeft?: number          // 投票剩余时间（秒）
  votingVotedCount?: number        // 已投票人数
  votingResult?: Record<string, any>  // 投票结果
  playerVotes?: Record<number, any>   // 玩家投票状态
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

// 推进发言者
export type AdvanceSpeakerRequest = {
  roomId: string
}

export type AdvanceSpeakerResponse = {
  success: boolean
  currentSpeaker?: number
}

// Agent 投票
export type AgentVoteRequest = {
  roomId: string
  seat: number  // Agent 的座位号
}

export type AgentVoteResponse = {
  success: boolean
  seat: number
  targetSeat: number
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

// ============== API 调用 ==============

export async function assignRoles(req: AssignRolesRequest): Promise<AssignRolesResponse> {
  return await request<AssignRolesResponse, AssignRolesRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/assign-roles`,
    data: req,
  })
}

export async function getGameState(req: GameStateRequest): Promise<GameStateResponse> {
  return await request<GameStateResponse, GameStateRequest>({
    method: 'GET',
    path: `/rooms/${encodeURIComponent(req.roomId)}/state`,
  })
}

export async function startRound(req: StartRoundRequest): Promise<StartRoundResponse> {
  return await request<StartRoundResponse, StartRoundRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/start-round`,
    data: req,
  })
}

export async function submitSpeech(req: SubmitSpeechRequest): Promise<SubmitSpeechResponse> {
  return await request<SubmitSpeechResponse, SubmitSpeechRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/speech`,
    data: req,
  })
}

export async function submitVote(req: SubmitVoteRequest): Promise<SubmitVoteResponse> {
  return await request<SubmitVoteResponse, SubmitVoteRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/vote`,
    data: req,
  })
}

export async function submitNightAction(req: SubmitNightActionRequest): Promise<SubmitNightActionResponse> {
  return await request<SubmitNightActionResponse, SubmitNightActionRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/night-action`,
    data: req,
  })
}

export async function getGameMessages(req: GetGameMessagesRequest): Promise<GetGameMessagesResponse> {
  return await request<GetGameMessagesResponse, GetGameMessagesRequest>({
    method: 'GET',
    path: `/rooms/${encodeURIComponent(req.roomId)}/messages${req.lastMessageId ? `?after=${req.lastMessageId}` : ''}`,
  })
}

export async function getAgentSpeech(req: GetAgentSpeechRequest): Promise<GetAgentSpeechResponse> {
  return await request<GetAgentSpeechResponse, GetAgentSpeechRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/agent-speech`,
    data: req,
  })
}

export async function advanceSpeaker(req: AdvanceSpeakerRequest): Promise<AdvanceSpeakerResponse> {
  return await request<AdvanceSpeakerResponse, AdvanceSpeakerRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/advance-speaker`,
    data: req,
  })
}

export async function agentVote(req: AgentVoteRequest): Promise<AgentVoteResponse> {
  return await request<AgentVoteResponse, AgentVoteRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/agent-vote`,
    data: req,
  })
}

export async function getAgentAction(req: GetAgentActionRequest): Promise<GetAgentActionResponse> {
  return await request<GetAgentActionResponse, GetAgentActionRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/agent-action`,
    data: req,
  })
}

// 完成播报
export type CompleteAnnouncementRequest = {
  roomId: string
}

export type CompleteAnnouncementResponse = {
  success: boolean
}

export async function completeAnnouncement(req: CompleteAnnouncementRequest): Promise<CompleteAnnouncementResponse> {
  return await request<CompleteAnnouncementResponse, CompleteAnnouncementRequest>({
    method: 'POST',
    path: `/rooms/${encodeURIComponent(req.roomId)}/complete-announcement`,
    data: req,
  })
}

