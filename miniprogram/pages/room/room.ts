import {
    advanceSpeaker,
    assignRoles,
    GamePhase,
    getGameState,
    Role,
    startRound,
    submitSpeech,
    submitVote
} from '../../services/gameApi'
import {formatTime} from '../../utils/util'

type StoredUserProfile = {
  avatarUrl: string
  nickName: string
}

type PlayerView = {
  seat: number
  nickName: string
  avatarUrl: string
  isMe: boolean
  alive?: boolean
}

type Speech = {
  id: string
  seat: number
  at: string
  text: string
}

type GameUIPhase = 'waiting' | 'role_assigned' | 'discussing' | 'voting' | 'night' | 'result' | 'game_over'

const STORAGE_KEY_PROFILE = 'ww_user_profile'
const STORAGE_KEY_SEAT_PREFIX = 'ww_room_seat_'

const AGENT_AVATAR_URL =
  'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

function loadStoredProfile(): StoredUserProfile | null {
  const v = wx.getStorageSync(STORAGE_KEY_PROFILE) as unknown
  if (!v || typeof v !== 'object') return null
  const maybe = v as Partial<StoredUserProfile>
  if (!maybe.avatarUrl || !maybe.nickName) return null
  return { avatarUrl: maybe.avatarUrl, nickName: maybe.nickName }
}

function randomSeat(seatCount: number): number {
  return Math.floor(Math.random() * seatCount) + 1
}

function roleText(role: Role): string {
  switch (role) {
    case 'werewolf':
      return '狼人'
    case 'villager':
      return '村民'
    case 'seer':
      return '预言家'
    case 'witch':
      return '女巫'
    case 'hunter':
      return '猎人'
    default:
      return role
  }
}

Component({
  data: {
    roomId: '',
    seatCount: 12,
    mySeat: 0,
    players: [] as PlayerView[],
    leftPlayers: [] as PlayerView[],
    rightPlayers: [] as PlayerView[],
    phase: 'waiting' as GameUIPhase,
    phaseText: '等待开始',
    myRole: '' as string,
    myRoleZh: '' as string,
    round: 0,
    speeches: [] as Speech[],
    speechDraft: '',
    alivePlayers: [] as number[],
    deadPlayers: [] as number[],

    // 后端实时状态（完全由后端驱动）
    currentSpeaker: 0,
    speakingOrder: [] as number[],
    currentSpeakerIndex: 0,
    speakingTimeLeft: 0,
    phaseTimeLeft: 0,

    votingTimeLeft: 0,
    votingVotedCount: 0,
    votingResult: null as Record<string, any> | null,
    playerVotes: {} as Record<number, any>,
    myVote: 0,

    // 轮询控制
    _pollingTimer: 0,
  },
  lifetimes: {
    attached() {
      const profile = loadStoredProfile()
      if (!profile) {
        wx.showToast({ title: '请先在房间列表页获取头像昵称', icon: 'none' })
        wx.navigateBack()
        return
      }

      const pages = getCurrentPages()
      const current = pages[pages.length - 1] as unknown as { options?: Record<string, string> }
      const roomId = current.options?.roomId ?? 'classic'

      const seatCount = this.data.seatCount
      const seatKey = `${STORAGE_KEY_SEAT_PREFIX}${roomId}`
      const storedSeat = wx.getStorageSync(seatKey) as unknown
      const mySeat = typeof storedSeat === 'number' && storedSeat >= 1 && storedSeat <= seatCount ? storedSeat : randomSeat(seatCount)
      wx.setStorageSync(seatKey, mySeat)

      const players: PlayerView[] = Array.from({ length: seatCount }, (_, idx) => {
        const seat = idx + 1
        const isMe = seat === mySeat
        return {
          seat,
          isMe,
          nickName: isMe ? profile.nickName : `Agent ${seat}`,
          avatarUrl: isMe ? profile.avatarUrl : AGENT_AVATAR_URL,
        }
      })

      // 将玩家分为左右两组
      const halfCount = Math.ceil(seatCount / 2)
      const leftPlayers = players.slice(0, halfCount)
      const rightPlayers = players.slice(halfCount)

      this.setData({
        roomId,
        mySeat,
        players,
        leftPlayers,
        rightPlayers,
        phase: 'waiting',
        phaseText: '等待开始',
        myRole: '',
        speechDraft: '',
      })
    },
    detached() {
      this.stopPolling()
    },
  },
  methods: {
    // ========== 游戏初始化 ==========
    async startGame() {
      if (this.data.phase !== 'waiting') return
      wx.showLoading({ title: '分配角色中...' })
      try {
        const res = await assignRoles({
          roomId: this.data.roomId,
          seatCount: this.data.seatCount,
          userSeat: this.data.mySeat,
        })

        const roleData = (res as any).data || res
        const mySeat = this.data.mySeat
        const myRole = roleData.rolesBySeat[mySeat]

        this.setData({
          phase: 'role_assigned',
          phaseText: '角色已分配，准备开始',
          myRole: myRole,
          myRoleZh: myRole ? roleText(myRole) : '',
          alivePlayers: Array.from({ length: this.data.seatCount }, (_, i) => i + 1),
          deadPlayers: [],
        })

        // 启动轮询
        this.startPolling()
      } catch (e) {
        console.error('分配角色异常:', e)
        wx.showToast({ title: '分配角色失败', icon: 'none' })
      } finally {
        wx.hideLoading()
      }
    },

    // ========== 纯轮询模式 ==========
    startPolling() {
      this.stopPolling()

      // 立即执行一次，然后每秒轮询一次
      this.pollGameState()
      const self = this as unknown as { _pollingTimer?: number }
      self._pollingTimer = setInterval(() => {
        this.pollGameState()
      }, 1000) as unknown as number
    },

    stopPolling() {
      const self = this as unknown as { _pollingTimer?: number }
      if (self._pollingTimer) {
        clearInterval(self._pollingTimer as number)
        self._pollingTimer = undefined
      }
    },

    async pollGameState() {
      try {
        // 推进游戏阶段
        await startRound({ roomId: this.data.roomId })

        // 获取完整游戏状态
        const gameState = await getGameState({ roomId: this.data.roomId })
        const { uiPhase, phaseText } = this.mapGamePhase(gameState.phase)

        // 仅同步后端状态到UI，所有UI都来自后端
        this.setData({
          phase: uiPhase,
          phaseText,
          round: gameState.round,
          alivePlayers: gameState.alivePlayers,
          deadPlayers: gameState.deadPlayers,
          currentSpeaker: gameState.currentSpeaker || 0,
          speakingOrder: gameState.speakingOrder || [],
          currentSpeakerIndex: gameState.currentSpeakerIndex || 0,
          speakingTimeLeft: gameState.speakingTimeLeft || 0,
          phaseTimeLeft: gameState.phaseTimeLeft || 0,
          votingTimeLeft: gameState.votingTimeLeft || 0,
          votingVotedCount: gameState.votingVotedCount || 0,
          votingResult: gameState.votingResult || null,
          playerVotes: gameState.playerVotes || {},
        })
      } catch (e) {
        console.error('轮询失败:', e)
      }
    },

    mapGamePhase(backendPhase: GamePhase): { uiPhase: GameUIPhase; phaseText: string } {
      const mapping: Record<GamePhase, { uiPhase: GameUIPhase; phaseText: string }> = {
        'waiting': { uiPhase: 'waiting', phaseText: '等待中' },
        'role_assigned': { uiPhase: 'role_assigned', phaseText: '角色已分配' },
        'day_discussion': { uiPhase: 'discussing', phaseText: '白天讨论' },
        'day_voting': { uiPhase: 'voting', phaseText: '白天投票' },
        'night_action': { uiPhase: 'night', phaseText: '晚上行动' },
        'day_result': { uiPhase: 'result', phaseText: '投票结果' },
        'night_result': { uiPhase: 'result', phaseText: '晚上结果' },
        'game_over': { uiPhase: 'game_over', phaseText: '游戏结束' },
      }
      return mapping[backendPhase] || { uiPhase: 'waiting', phaseText: '未知阶段' }
    },

    // ========== 玩家操作 ==========
    onSpeechInput(e: { detail: { value: string } }) {
      this.setData({ speechDraft: e.detail.value })
    },

    async submitSpeech() {
      const text = (this.data.speechDraft || '').trim()
      if (!text) {
        wx.showToast({ title: '请输入发言内容', icon: 'none' })
        return
      }

      if (text.length > 300) {
        wx.showToast({ title: '发言内容过长', icon: 'none' })
        return
      }

      try {
        // 提交发言到后端
        await submitSpeech({
          roomId: this.data.roomId,
          seat: this.data.mySeat,
          text,
        })

        // 添加到本地发言列表显示
        const now = formatTime(new Date())
        const speech: Speech = {
          id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
          seat: this.data.mySeat,
          at: now,
          text,
        }

        this.setData({
          speeches: [speech, ...this.data.speeches],
          speechDraft: '',
        })

        wx.showToast({ title: '发言已提交', icon: 'success' })

        // 触发发言者推进（后端将处理轮流）
        await advanceSpeaker({ roomId: this.data.roomId })
      } catch (e) {
        console.error('发言提交失败:', e)
        wx.showToast({ title: '发言提交失败', icon: 'none' })
      }
    },

    async submitMyVote(e: { target: { dataset: { target: string } } }) {
      const targetSeatStr = e.target.dataset.target
      const targetSeat = targetSeatStr ? parseInt(targetSeatStr, 10) : 0
      const mySeat = this.data.mySeat

      if (targetSeat <= 0 || !this.data.alivePlayers.includes(targetSeat)) {
        wx.showToast({ title: '投票目标无效', icon: 'none' })
        return
      }

      try {
        // 提交投票到后端
        await submitVote({
          roomId: this.data.roomId,
          voterSeat: mySeat,
          targetSeat,
        })

        this.setData({ myVote: targetSeat })
        wx.showToast({ title: '投票已提交', icon: 'success' })
      } catch (e) {
        console.error('投票提交失败:', e)
        wx.showToast({ title: '投票提交失败', icon: 'none' })
      }
    },
  },
})

