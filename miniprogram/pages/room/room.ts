import {
  advanceSpeaker,
  agentVote,
  assignRoles,
  completeAnnouncement,
  GamePhase,
  getAgentAction,
  getAgentSpeech,
  getGameState,
  Role,
  startRound,
  submitNightAction,
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

    // 角色信息（从后端获取并存储）
    rolesBySeat: {} as Record<number, string>,

    // 轮询控制
    _pollingTimer: 0,

    // 防止重复弹窗标志
    _showingAnnouncement: false,

    // 跟踪已处理过的发言者
    _processedSpeakers: [] as number[],

    // 跟踪前一阶段，用于检测阶段切换
    _lastGamePhase: '' as string,

    // 轮询执行标志，防止并发重复执行
    _isPolling: false,

    // 夜晚行动状态
    nightPhaseTip: '',
    waitingText: '',
    isMyTurn: false,
    selectedNightTarget: 0,
    selectedWitchAction: '' as string,
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
          rolesBySeat: roleData.rolesBySeat,
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
      // 防止并发执行：如果上一次轮询还没完成，直接返回
      if ((this as any)._isPolling) {
        console.log('[pollGameState] 上一次轮询还在执行中，跳过本次')
        return
      }

      (this as any)._isPolling = true

      try {
        // 获取完整游戏状态
        const gameData = await getGameState({ roomId: this.data.roomId })
        const { uiPhase, phaseText } = this.mapGamePhase(gameData.phase)

        // 添加调试日志
        if (gameData.phase === 'night_action') {
          console.log('[pollGameState] night_action 阶段 gameData:', {
            phase: gameData.phase,
            currentRole: (gameData as any).currentRole,
            actionRole: (gameData as any).actionRole,
            nightTimeLeft: (gameData as any).nightTimeLeft,
            alivePlayers: gameData.alivePlayers,
            nightActionsCompleted: (gameData as any).nightActionsCompleted,
            rolesBySeat: (gameData as any).rolesBySeat
          })
        }

        // 检查是否需要播报（播报是附加信息，不影响游戏状态）
        if ((gameData as any).announcement) {
          // 显示播报弹窗
          const announcement = (gameData as any).announcement
          const self = this

          // 防止重复弹窗
          if (!(this as any)._showingAnnouncement) {
            (this as any)._showingAnnouncement = true
            wx.showModal({
              title: '提示',
              content: announcement,
              showCancel: false,
              success: async () => {
                // 播报完成后，调用后端清除播报信息
                (self as any)._showingAnnouncement = false

                try {
                  await completeAnnouncement({ roomId: self.data.roomId })
                } catch (e) {
                  console.error('清除播报失败:', e)
                }

                // 如果是角色分配完成，播报后启动游戏
                if (gameData.phase === 'role_assigned') {
                  try {
                    await startRound({ roomId: self.data.roomId })
                  } catch (e) {
                    console.error('启动游戏失败:', e)
                    wx.showToast({ title: '启动游戏失败', icon: 'none' })
                  }
                }
              },
            })
          }
        }

        // 检测阶段切换，只在进入新阶段时执行初始化
        const lastPhase = (this as any)._lastGamePhase || ''
        const currentPhase = gameData.phase
        let phaseChanged = false
        if (lastPhase !== currentPhase) {
          phaseChanged = true
        }

        // 立即更新前一阶段记录，防止异步轮询重复检测切换
        (this as any)._lastGamePhase = currentPhase

        // 根据不同阶段执行不同的操作
        switch (currentPhase) {
          case 'day_discussion':
            // 只在首次进入白天讨论阶段时清空已处理过的发言者
            if (phaseChanged) {
              console.log(`[pollGameState] 阶段切换到 day_discussion，清空已处理列表`)
              this.setData({ _processedSpeakers: [] })
            }
            await this.handleDayDiscussion(gameData)
            break
          case 'day_voting':
            await this.handleDayVoting(gameData)
            break
          case 'night_action':
            await this.handleNightAction(gameData)
            break
          case 'day_result':
          case 'night_result':
            await this.handleResult(gameData)
            break
          case 'game_over':
            this.handleGameOver(gameData)
            break
        }

        // 同步后端状态到UI
        this.setData({
          phase: uiPhase,
          phaseText,
          round: gameData.round,
          alivePlayers: gameData.alivePlayers,
          deadPlayers: gameData.deadPlayers,
          currentSpeaker: gameData.currentSpeaker || 0,
          speakingOrder: gameData.speakingOrder || [],
          currentSpeakerIndex: gameData.currentSpeakerIndex || 0,
          speakingTimeLeft: gameData.speakingTimeLeft || 0,
          phaseTimeLeft: gameData.phaseTimeLeft || 0,
          votingTimeLeft: gameData.votingTimeLeft || 0,
          votingVotedCount: gameData.votingVotedCount || 0,
          votingResult: gameData.votingResult || null,
          playerVotes: gameData.playerVotes || {},
        })
      } catch (e) {
        console.error('轮询失败:', e)
      } finally {
        // 无论成功或失败，都要重置轮询标志
        (this as any)._isPolling = false
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
        'announcing': { uiPhase: 'result', phaseText: '主持人播报中' },
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

    // ========== 阶段处理方法 ==========

    async handleDayDiscussion(gameData: any) {
      const currentSpeaker = gameData.currentSpeaker || 0
      const mySeat = this.data.mySeat

      // 检查是否已经处理过该发言者
      const processedSpeakers = this.data._processedSpeakers || []
      console.log(`[handleDayDiscussion] 当前发言者: ${currentSpeaker}, 已处理:`, processedSpeakers)

      if (currentSpeaker !== 0 && !processedSpeakers.includes(currentSpeaker)) {
        // 先添加到已处理列表，防止并发重复执行
        const newProcessedSpeakers = [...processedSpeakers, currentSpeaker]
        console.log(`[handleDayDiscussion] 将 ${currentSpeaker} 号添加到已处理列表`)
        this.setData({ _processedSpeakers: newProcessedSpeakers })

        // 如果当前发言者是 Agent，获取并显示 Agent 的发言
        if (currentSpeaker !== mySeat && this.data.alivePlayers.includes(currentSpeaker)) {
          const player = this.data.players.find(p => p.seat === currentSpeaker)
          if (player && !player.isMe) {
            // 这是 Agent，获取其发言
            try {
              const agentSpeech = await getAgentSpeech({
                roomId: this.data.roomId,
                seat: currentSpeaker,
              })

              // 添加到本地发言列表
              const now = formatTime(new Date())
              const speech: Speech = {
                id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
                seat: currentSpeaker,
                at: now,
                text: agentSpeech.text,
              }

              // 检查是否已经存在该发言
              const exists = this.data.speeches.some(s => s.text === speech.text && s.seat === speech.seat)
              if (!exists) {
                this.setData({
                  speeches: [speech, ...this.data.speeches],
                })
              }

              // 推进到下一个发言者
              await advanceSpeaker({ roomId: this.data.roomId })
            } catch (e) {
              console.error('获取 Agent 发言失败:', e)
              // 失败时从已处理列表中移除，下次轮询可以重试
              const updatedProcessedSpeakers = this.data._processedSpeakers.filter(s => s !== currentSpeaker)
              console.log(`[handleDayDiscussion] 将 ${currentSpeaker} 号从已处理列表移除，允许重试`)
              this.setData({ _processedSpeakers: updatedProcessedSpeakers })
            }
          }
        }
      }
    },

    async handleDayVoting(gameData: any) {
      const playerVotes = gameData.playerVotes || {}

      // 检查是否有 Agent 还没投票
      for (const [seat, voteStatus] of Object.entries(playerVotes)) {
        const seatNum = parseInt(seat, 10)
        const player = this.data.players.find(p => p.seat === seatNum)

        // 如果是 Agent 且还没投票，触发后端让其投票
        if (player && !player.isMe && !(voteStatus as any).hasVoted) {
          try {
            await agentVote({
              roomId: this.data.roomId,
              seat: seatNum,
            })
          } catch (e) {
            console.error(`Agent ${seatNum} 号投票失败:`, e)
          }
        }
      }
    },

    async handleNightAction(gameData: any) {
      const myRole = this.data.myRole
      const currentRole = gameData.currentRole as string || gameData.actionRole || ''
      const nightTimeLeft = gameData.nightTimeLeft || 0

      console.log(`[handleNightAction] myRole=${myRole}, currentRole=${currentRole}, nightTimeLeft=${nightTimeLeft}`)

      // 检查是否轮到我的角色
      const isMyTurn = currentRole === myRole
      this.setData({ isMyTurn })

      // 晚上行动阶段：Agent 由前端触发后端接口
      // 遍历所有玩家，找到当前需要行动的 Agent
      for (const player of this.data.players) {
        // 只处理存活的玩家
        if (!this.data.alivePlayers.includes(player.seat)) {
          const playerRole = this.getRoleBySeat(player.seat)
          console.log(`[handleNightAction] 跳过 ${player.seat} (已死亡), 角色=${playerRole}`)
          continue
        }

        // 检查是否轮到该角色的行动
        // 从本地获取该玩家的角色信息
        const playerRole = this.getRoleBySeat(player.seat)

        console.log(`[handleNightAction] 玩家 ${player.seat} 角色=${playerRole}, isMe=${player.isMe}`)

        if (!playerRole || !['werewolf', 'seer', 'witch'].includes(playerRole)) {
          console.log(`[handleNightAction] 跳过 ${player.seat} (角色不匹配: ${playerRole})`)
          continue
        }

        // 检查是否轮到这个角色行动
        if (currentRole !== playerRole) {
          console.log(`[handleNightAction] 跳过 ${player.seat} (当前不是该角色行动: ${playerRole} != ${currentRole})`)
          continue
        }

        // 检查是否是 Agent
        if (!player.isMe) {
          // 这是 Agent，前端触发后端接口
          console.log(`[handleNightAction] 触发 Agent ${player.seat} (${playerRole}) 行动`)
          try {
            // 获取 Agent 的行动决策
            const agentAction = await getAgentAction({
              roomId: this.data.roomId,
              seat: player.seat,
              role: playerRole as Role,
              availableTargets: gameData.alivePlayers || [],
            })
            console.log(`Agent ${player.seat} (${playerRole}) 决策了 ${agentAction.actionType} 行动`, agentAction)

          // 提交 Agent 的行动到后端
          console.log(`[handleNightAction] 准备提交 Agent 行动:`, {
            seat: player.seat,
            role: playerRole,
            actionType: agentAction.actionType,
            targetSeat: agentAction.targetSeat || 0
          })
          await submitNightAction({
              roomId: this.data.roomId,
              playerSeat: player.seat,
              role: playerRole as Role,
              actionType: agentAction.actionType as 'kill' | 'check' | 'save' | 'poison',
              targetSeat: agentAction.targetSeat || 0
            })
            console.log(`Agent ${player.seat} (${playerRole}) 的行动已提交`)
          } catch (e) {
            console.error(`Agent ${player.seat} 行动失败:`, e)
          }
        } else {
          console.log(`[handleNightAction] ${player.seat} 是玩家，需要手动操作`)
        }
      }

      // 更新提示文本
      this.updateNightTipText(gameData)

      // 如果还有剩余时间，继续轮询让后端处理超时
      if (nightTimeLeft > 0) {
        // 可以在这里显示倒计时提示
        console.log(`晚上行动剩余时间: ${nightTimeLeft}秒`)
      }
    },

    updateNightTipText(gameData: any) {
      const myRole = this.data.myRole
      const currentRole = gameData.currentRole as string || gameData.actionRole || ''

      // 根据当前角色和是否轮到我，更新提示文本
      if (currentRole === myRole) {
        const roleMap: Record<string, string> = {
          'werewolf': '请选择击杀目标',
          'witch': '请选择是否使用药水',
          'seer': '请选择查验目标'
        }
        this.setData({
          nightPhaseTip: roleMap[myRole as string] || '',
          waitingText: ''
        })
      } else {
        const roleName: Record<string, string> = { 'werewolf': '狼人', 'witch': '女巫', 'seer': '预言家' }
        this.setData({
          nightPhaseTip: '请等待其他角色行动',
          waitingText: `${roleName[currentRole as string] || currentRole}正在行动中...`
        })
      }
    },

    // 辅助方法：根据座位号获取角色
    getRoleBySeat(seat: number): string | null {
      if (!this.data.rolesBySeat) return null
      return this.data.rolesBySeat[seat] || null
    },

    // 夜晚操作相关方法
    selectNightTarget(e: any) {
      const target = e.currentTarget.dataset.target as number
      this.setData({ selectedNightTarget: target })
    },

    selectWitchAction(e: any) {
      const action = e.currentTarget.dataset.action as string
      this.setData({ selectedWitchAction: action })
    },

    getWitchActionText(): string {
      switch (this.data.selectedWitchAction) {
        case 'save':
          return '使用解药'
        case 'poison':
          return '使用毒药'
        default:
          return '选择目标'
      }
    },

    async submitNightAction() {
      const mySeat = this.data.mySeat
      const myRole = this.data.myRole

      if (!this.data.isMyTurn) {
        wx.showToast({ title: '还没轮到你', icon: 'none' })
        return
      }

      try {
        if (myRole === 'werewolf' || myRole === 'seer') {
          const target = this.data.selectedNightTarget
          if (!target) {
            wx.showToast({ title: '请选择目标', icon: 'none' })
            return
          }

          await submitNightAction({
            roomId: this.data.roomId,
            playerSeat: mySeat,
            role: myRole as Role,
            actionType: myRole === 'werewolf' ? 'kill' : 'check',
            targetSeat: target
          })

          this.setData({ selectedNightTarget: 0 })
        } else if (myRole === 'witch') {
          const action = this.data.selectedWitchAction
          if (!action || action === 'none') {
            wx.showToast({ title: '请选择药水', icon: 'none' })
            return
          }

          const targetSeat = action === 'save' ? this.data.selectedNightTarget : 0

          await submitNightAction({
            roomId: this.data.roomId,
            playerSeat: mySeat,
            role: myRole as Role,
            actionType: action as 'kill' | 'check' | 'save' | 'poison',
            targetSeat: targetSeat
          })

          this.setData({ selectedWitchAction: '', selectedNightTarget: 0 })
        }
      } catch (e) {
        console.error('提交夜晚行动失败:', e)
        wx.showToast({ title: '提交失败', icon: 'none' })
      }
    },

    async handleResult(gameData: any) {
      // 结果阶段，显示死亡信息
      if (gameData.lastDeadPlayer) {
        const { seat, role, killedBy } = gameData.lastDeadPlayer
        const killedByText = killedBy === 'vote' ? '被投票出局' :
                            killedBy === 'werewolf' ? '被狼人杀死' :
                            '被女巫毒死'
        const roleTextZh = roleText(role)
        wx.showToast({
          title: `玩家 ${seat} 号 (${roleTextZh}) ${killedByText}`,
          icon: 'none',
          duration: 3000,
        })
      }
    },

    handleGameOver(gameData: any) {
      // 游戏结束
      const result = gameData.result
      const resultText = result === 'werewolf_win' ? '狼人胜利' :
                        result === 'villager_win' ? '好人阵营胜利' :
                        '游戏结束'
      wx.showModal({
        title: '游戏结束',
        content: resultText,
        showCancel: false,
        success: () => {
          wx.navigateBack()
        },
      })
    },
  },
})

