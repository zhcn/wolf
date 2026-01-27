import {
  assignRoles,
  GamePhase,
  getAgentSpeech,
  getGameState,
  Role,
  startRound,
  submitSpeech,
  submitVote,
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
    timeLeft: 0,
    speeches: [] as Speech[],
    speechDraft: '',
    alivePlayers: [] as number[],
    deadPlayers: [] as number[],
    currentSpeaker: 0,  // 当前发言者座位号
    speakingOrder: [] as number[],  // 发言顺序（存活玩家列表）
    currentSpeakerIndex: 0,  // 当前在发言顺序中的索引
    speakingTimeLeft: 60,  // 当前发言者剩余发言时间
    // 游戏流程控制
    _gameLoopTimer: 0,
    _stateCheckTimer: 0,
    _speakingTimer: 0,  // 发言倒计时计时器
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
        speakingTimeLeft: 60,
        speechDraft: '',
      })
    },
    detached() {
      this.stopGameLoop()
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
        console.log('分配角色成功，原始响应:', res)

        // 处理响应结构（可能被多层包装）
        const roleData = (res as any).data || res
        console.log('提取后的角色数据:', roleData)

        const mySeat = this.data.mySeat
        const rolesBySeat = roleData.rolesBySeat
        console.log('rolesBySeat:', rolesBySeat, 'mySeat:', mySeat)

        const myRole = rolesBySeat[mySeat]
        this.setData({
          phase: 'role_assigned',
          phaseText: '角色已分配，准备开始',
          myRole: myRole,
          myRoleZh: myRole ? roleText(myRole) : '',
          alivePlayers: Array.from({ length: this.data.seatCount }, (_, i) => i + 1),
          deadPlayers: [],
        })

        // 启动游戏循环
        this.startGameLoop()
      } catch (e) {
        console.error('分配角色异常:', e)
        const errorMsg = e instanceof Error ? e.message : String(e)
        wx.showToast({ title: `分配角色失败: ${errorMsg}`, icon: 'none' })
      } finally {
        wx.hideLoading()
      }
    },

    // ========== 游戏循环控制 ==========
    startGameLoop() {
      this.stopGameLoop()

      // 3秒后开始第一轮
      const self = this as unknown as { _gameLoopTimer?: number }
      self._gameLoopTimer = setTimeout(() => {
        this.advanceGameRound()
      }, 3000) as unknown as number
    },

    stopGameLoop() {
      const self = this as unknown as { _gameLoopTimer?: number; _stateCheckTimer?: number }
      if (self._gameLoopTimer) {
        clearTimeout(self._gameLoopTimer)
        self._gameLoopTimer = undefined
      }
      if (self._stateCheckTimer) {
        clearInterval(self._stateCheckTimer)
        self._stateCheckTimer = undefined
      }
    },

    async advanceGameRound() {
      try {
        console.log('[advanceGameRound] 开始请求...')
        const res = await startRound({ roomId: this.data.roomId })
        console.log('[advanceGameRound] startRound 完整响应:', res)

        // 处理响应结构（可能被多层包装）
        const roundData = (res as any).data || res
        console.log('[advanceGameRound] 提取后的数据:', roundData)
        console.log('[advanceGameRound] roundData.phase:', roundData?.phase)
        console.log('[advanceGameRound] roundData.durationSeconds:', roundData?.durationSeconds)

        if (!roundData || !roundData.phase) {
          throw new Error(`响应不完整: ${JSON.stringify(roundData)}`)
        }

        // 映射后端阶段到UI阶段
        const { uiPhase, phaseText } = this.mapGamePhase(roundData.phase)
        console.log('[advanceGameRound] 映射后:', { uiPhase, phaseText })

        // 确保 durationSeconds 有有效值
        const durationSeconds = roundData.durationSeconds ?? 60
        console.log('[advanceGameRound] 最终 durationSeconds:', durationSeconds)

        // 获取最新游戏状态以获取当前发言者
        console.log('[advanceGameRound] 获取游戏状态...')
        const gameState = await getGameState({ roomId: this.data.roomId })
        console.log('[advanceGameRound] 游戏状态:', gameState)

        // 如果进入讨论阶段，初始化发言顺序
        let speakingOrder = this.data.speakingOrder
        let currentSpeakerIndex = 0

        if (uiPhase === 'discussing' && gameState.alivePlayers && gameState.alivePlayers.length > 0) {
          speakingOrder = gameState.alivePlayers
          currentSpeakerIndex = 0
          console.log('[advanceGameRound] 初始化发言顺序:', speakingOrder)
        }

        this.setData({
          phase: uiPhase,
          phaseText,
          timeLeft: durationSeconds,
          currentSpeaker: speakingOrder[currentSpeakerIndex] || 0,
          round: gameState.round,
          alivePlayers: gameState.alivePlayers,
          deadPlayers: gameState.deadPlayers,
          speakingOrder,
          currentSpeakerIndex,
          speakingTimeLeft: 60,  // 每个发言者60秒
        })

        // 如果进入讨论阶段，启动发言倒计时
        if (uiPhase === 'discussing') {
          this.startSpeakingTimer()
        } else {
          // 否则启动阶段倒计时
          this.startPhaseCountdown(durationSeconds)
        }
      } catch (e) {
        console.error('[advanceGameRound] 推进游戏阶段失败', e)
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

    startPhaseCountdown(seconds: number) {
      const self = this as unknown as { _stateCheckTimer?: number }
      if (self._stateCheckTimer) {
        clearInterval(self._stateCheckTimer)
      }

      let remaining = seconds
      self._stateCheckTimer = setInterval(() => {
        remaining--
        this.setData({ timeLeft: remaining })

        if (remaining <= 0) {
          clearInterval(self._stateCheckTimer)
          self._stateCheckTimer = undefined
          // 自动进入下一阶段
          this.advanceGameRound()
        }
      }, 1000) as unknown as number
    },

    startSpeakingTimer() {
      const self = this as unknown as { _speakingTimer?: number }
      if (self._speakingTimer) {
        clearInterval(self._speakingTimer)
      }

      let remaining = 60  // 每个人最多发言60秒
      self._speakingTimer = setInterval(() => {
        remaining--
        this.setData({ speakingTimeLeft: remaining })

        if (remaining <= 0) {
          clearInterval(self._speakingTimer)
          self._speakingTimer = undefined
          // 时间到，轮到下一个人发言
          this.nextSpeaker()
        }
      }, 1000) as unknown as number
    },

    async nextSpeaker() {
      console.log('[nextSpeaker] 切换到下一个发言者')
      const currentIndex = this.data.currentSpeakerIndex
      const nextIndex = currentIndex + 1

      if (nextIndex >= this.data.speakingOrder.length) {
        // 所有人都发言完了，进入投票阶段
        console.log('[nextSpeaker] 所有人都发言完了，结束讨论阶段')
        this.advanceGameRound()
        return
      }

      const nextSeat = this.data.speakingOrder[nextIndex]
      console.log('[nextSpeaker] 下一个发言者:', nextSeat)

      this.setData({
        currentSpeaker: nextSeat,
        currentSpeakerIndex: nextIndex,
        speakingTimeLeft: 60,
      })

      // 如果下一个发言者是 agent（不是玩家自己），自动为其获取发言并提交
      if (nextSeat !== this.data.mySeat) {
        console.log('[nextSpeaker] 下一个发言者是 Agent，自动获取发言')
        await this.autoSubmitAgentSpeech(nextSeat)
      } else {
        console.log('[nextSpeaker] 下一个发言者是玩家，等待玩家提交')
        // 重新启动发言倒计时
        this.startSpeakingTimer()
      }
    },

    async autoSubmitAgentSpeech(agentSeat: number) {
      try {
        console.log('[autoSubmitAgentSpeech] 为 Agent 获取发言...')
        const speechRes = await getAgentSpeech({
          roomId: this.data.roomId,
          seat: agentSeat,
        })

        const now = formatTime(new Date())
        const speech: Speech = {
          id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
          seat: agentSeat,
          at: now,
          text: speechRes.text,
        }

        console.log('[autoSubmitAgentSpeech] Agent 发言:', speech.text)

        // 提交 Agent 的发言
        await submitSpeech({
          roomId: this.data.roomId,
          seat: agentSeat,
          text: speechRes.text,
        })

        // 更新发言列表
        this.setData({
          speeches: [speech, ...this.data.speeches],
        })

        // 稍等一下，然后轮到下一个人
        setTimeout(() => {
          this.nextSpeaker()
        }, 2000)  // 等待2秒后再轮到下一个人
      } catch (e) {
        console.error('[autoSubmitAgentSpeech] 错误:', e)
        // 错误时也轮到下一个人
        this.nextSpeaker()
      }
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
        console.log('[submitSpeech] 提交发言...')
        await submitSpeech({
          roomId: this.data.roomId,
          seat: this.data.mySeat,
          text,
        })
        console.log('[submitSpeech] 发言已提交')

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

        wx.showToast({ title: '发言已提交，轮到下一个人', icon: 'success' })

        // 发言后轮到下一个人
        this.nextSpeaker()
      } catch (e) {
        console.error('[submitSpeech] 错误:', e)
        wx.showToast({ title: '发言提交失败', icon: 'none' })
      }
    },

    async submitMyVote(e: { target: { dataset: { target: string } } }) {
      const targetSeat = parseInt(e.target.dataset.target)
      if (!targetSeat || !this.data.alivePlayers.includes(targetSeat)) {
        wx.showToast({ title: '目标玩家无效', icon: 'none' })
        return
      }

      try {
        const res = await submitVote({
          roomId: this.data.roomId,
          voterSeat: this.data.mySeat,
          targetSeat,
        })

        if (res.success) {
          wx.showToast({ title: '投票已提交', icon: 'success' })
        }
      } catch (e) {
        wx.showToast({ title: '投票提交失败', icon: 'none' })
      }
    },
  },
})

