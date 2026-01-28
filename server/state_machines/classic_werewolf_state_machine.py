"""
经典狼人杀状态机
实现经典狼人杀游戏的完整状态机逻辑
"""
import random
from datetime import datetime
from typing import Dict, Tuple, Any, Optional

from .base_state_machine import BaseStateMachine
from .state_context import GameStateContext
from .state_enums import Role, GameResult, KilledBy


class ClassicWerewolfStateMachine(BaseStateMachine):
    """
    经典狼人杀状态机

    阶段流程：
    waiting -> role_assigned -> day_discussion -> day_voting -> night_action -> day_discussion -> ...
    -> game_over

    角色配置（12人局）：
    - 2 个狼人
    - 1 个预言家
    - 1 个女巫
    - 1 个猎人
    - 7 个村民
    """

    # 12人局的默认角色配置
    DEFAULT_ROLES_12P = [
        Role.WEREWOLF, Role.WEREWOLF,  # 2 个狼人
        Role.SEER, Role.WITCH, Role.HUNTER,  # 特殊角色
        Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,  # 7 个村民
        Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER
    ]

    def __init__(self, room_id: str, seat_count: int = 12):
        self.seat_count = seat_count
        context = GameStateContext(room_id=room_id, mode='classic')
        super().__init__(room_id, 'classic', context)

        # 初始化玩家
        self._init_players()

    def initialize(self) -> None:
        """初始化经典狼人杀状态机"""
        # 注册阶段转换规则
        self._register_phase_transition('waiting', 'role_assigned', 0, self._on_role_assigned)
        self._register_phase_transition('role_assigned', 'day_discussion', 0, self._on_day_discussion_start)
        self._register_phase_transition('day_discussion', 'day_voting', 120, self._on_day_voting_start)  # 讨论2分钟
        self._register_phase_transition('day_voting', 'night_action', 20, self._on_night_action_start)  # 投票20秒
        self._register_phase_transition('night_action', 'day_discussion', 120, self._on_new_day)  # 晚上行动2分钟
        self._register_phase_transition('night_action', 'game_over', 0, self._on_game_over)  # 游戏结束

        # 注册动作处理器
        self._register_action_handler('vote', self._handle_vote)
        self._register_action_handler('speech', self._handle_speech)
        self._register_action_handler('night_action', self._handle_night_action)
        self._register_action_handler('advance_speaker', self._handle_advance_speaker)

    def assign_roles(self) -> Dict[int, str]:
        """
        分配角色

        返回:
            {座位号: 角色名称}
        """
        # 获取角色池
        if self.seat_count == 12:
            roles = self.DEFAULT_ROLES_12P.copy()
        else:
            roles = self._get_custom_roles(self.seat_count)

        # 随机洗牌
        random.shuffle(roles)

        # 为每个玩家分配角色
        for seat, role in enumerate(roles, start=1):
            if seat in self.context.players:
                self.context.players[seat].role = role

        # 更新游戏状态
        self.context.round = 1

        # 转换到角色分配阶段（会触发播报）
        self.transition_to('role_assigned')

        # 返回座位-角色映射
        return {
            seat: player.role.value
            for seat, player in self.context.players.items()
        }

    def _init_players(self):
        """初始化玩家对象"""
        for seat in range(1, self.seat_count + 1):
            self.context.players[seat] = self.context.get_player_by_seat(seat) or \
                                      __import__('state_machines.state_context', fromlist=['Player']).Player(seat=seat)

    def _get_custom_roles(self, count: int) -> list:
        """根据玩家数获取自定义角色配置"""
        werewolves = max(1, count // 6)  # 约 1/6 的狼人
        special_roles = min(3, count // 4)  # 特殊角色数
        villagers = count - werewolves - special_roles

        roles = (
            [Role.WEREWOLF] * werewolves +
            [Role.SEER, Role.WITCH, Role.HUNTER][:special_roles] +
            [Role.VILLAGER] * villagers
        )
        return roles

    def start_round(self) -> Tuple[str, int]:
        """推进游戏到下一阶段"""
        current_phase = self.context.phase
        next_phase, duration = self.get_next_phase(current_phase)

        # 特殊处理：如果是从night_action转出，需要先检查游戏是否结束
        if current_phase == 'night_action':
            if self._check_game_over():
                next_phase = 'game_over'
                duration = 0

        self.transition_to(next_phase)
        return next_phase, duration

    # === 阶段处理器 ===

    def _on_role_assigned(self):
        """角色分配完成时的处理"""
        # 初始化各角色的上下文信息
        self._init_role_contexts()

    def _init_role_contexts(self):
        """初始化各角色特定的上下文信息"""
        from .state_enums import Role

        # 初始化狼人上下文（队友列表）
        werewolf_teammates = [
            seat for seat, player in self.context.players.items()
            if player.role == Role.WEREWOLF
        ]
        self.context.werewolf_context = {
            'teammates': werewolf_teammates
        }

        # 初始化预言家上下文（空历史）
        self.context.seer_context = []

        # 初始化女巫上下文（药水状态）
        self.context.witch_context = {
            'has_save_potion': True,
            'has_poison_potion': True,
            'saved_history': []
        }

    def _on_day_discussion_start(self):
        """白天讨论开始时的处理"""
        self._init_speaking_order()

    def _on_day_voting_start(self):
        """白天投票开始时的处理"""
        self._init_voting()

    def _on_night_action_start(self):
        """晚上行动开始时的处理"""
        self._execute_voting()

        # 初始化晚上行动状态
        self.context.night_current_role = 'seer'  # 预言家先行动
        self.context.night_action_start_time = datetime.now().timestamp()
        self.context.night_actions_completed = []
        self.context.seer_checked = None
        self.context.werewolf_killed = None
        self.context.witch_saved = None
        self.context.witch_poisoned = None

    def _on_new_day(self):
        """新一天开始时的处理"""
        self._execute_night_actions()
        if not self._check_game_over():
            self.context.round += 1
            self._init_speaking_order()

    def _on_game_over(self):
        """游戏结束时的处理"""
        pass

    # === 动作处理器 ===

    def _handle_vote(self, payload: Dict) -> Tuple[bool, str, Any]:
        """
        处理投票动作

        参数:
            payload: {'voterSeat': 投票者座位, 'targetSeat': 目标座位}
        """
        voter_seat = payload.get('voterSeat')
        target_seat = payload.get('targetSeat')

        if voter_seat not in self.context.players or target_seat not in self.context.players:
            return False, "Invalid player seats", None

        voter = self.context.players[voter_seat]
        target = self.context.players[target_seat]

        if not voter.alive or not target.alive:
            return False, "Player is not alive", None

        # 如果之前没投过票，计数加1
        if not voter.has_voted:
            self.context.voting_voted_count += 1

        voter.voted_for = target_seat
        voter.has_voted = True

        # 检查是否所有活着的玩家都已投票
        alive_count = len(self.context.get_alive_players())
        if self.context.voting_voted_count >= alive_count:
            # 自动计算投票结果
            self._calculate_voting_result()

        return True, "Vote submitted successfully", {
            'voterSeat': voter_seat,
            'targetSeat': target_seat
        }

    def _handle_speech(self, payload: Dict) -> Tuple[bool, str, Any]:
        """
        处理发言动作

        参数:
            payload: {'seat': 发言者座位, 'text': 发言内容}
        """
        seat = payload.get('seat')
        text = payload.get('text', '')

        if not text or len(text) > 300:
            return False, "Invalid speech text", None

        return True, "Speech recorded successfully", {
            'seat': seat,
            'text': text
        }

    def _handle_night_action(self, payload: Dict) -> Tuple[bool, str, Any]:
        """
        处理晚上动作

        参数:
            payload: {'playerSeat': 玩家座位, 'role': 角色, 'actionType': 动作类型, 'targetSeat': 目标座位}
        """
        player_seat = payload.get('playerSeat')
        role = payload.get('role')
        action_type = payload.get('actionType')
        target_seat = payload.get('targetSeat')

        player = self.context.players.get(player_seat)
        if not player or not player.alive:
            return False, "Player not found or not alive", None

        if player.role.value != role:
            return False, "Role mismatch", None

        # 检查是否是当前行动的角色
        current_role = self.context.night_current_role
        if role != current_role:
            return False, f"Not your turn. Current: {current_role}, Your: {role}", None

        # 根据角色和动作类型处理
        announcement_text = None

        if action_type == 'kill' and role == 'werewolf':
            self.context.werewolf_killed = target_seat
            if target_seat:
                target_role = self.context.players[target_seat].role.value
                announcement_text = f"🐺 狼人 ({player_seat}号) 选择击杀了 {target_seat}号 ({target_role})"
        elif action_type == 'check' and role == 'seer':
            self.context.seer_checked = target_seat
            if target_seat:
                target_role = self.context.players[target_seat].role.value
                # 更新预言家上下文（记录查验历史）
                self.context.seer_context.append({
                    'round': self.context.round,
                    'seat': target_seat,
                    'result': target_role
                })
                announcement_text = f"🔮 预言家 ({player_seat}号) 查验了 {target_seat}号 ({target_role})"
        elif action_type == 'save' and role == 'witch':
            # 检查女巫是否还有药
            if self.context.witch_saved is not None:
                return False, "Witch already used save", None
            self.context.witch_saved = target_seat
            if target_seat:
                # 更新女巫上下文（记录救过的玩家）
                if self.context.witch_context:
                    self.context.witch_context['has_save_potion'] = False
                    self.context.witch_context['saved_history'].append(target_seat)
                announcement_text = f"💊 女巫 ({player_seat}号) 使用解药救了 {target_seat}号"
            else:
                if self.context.witch_context:
                    self.context.witch_context['has_save_potion'] = False
                announcement_text = f"💊 女巫 ({player_seat}号) 选择不使用解药"
        elif action_type == 'poison' and role == 'witch':
            # 检查女巫是否还有毒药
            if self.context.witch_poisoned is not None:
                return False, "Witch already used poison", None
            self.context.witch_poisoned = target_seat
            if target_seat:
                # 更新女巫上下文（使用毒药）
                if self.context.witch_context:
                    self.context.witch_context['has_poison_potion'] = False
                target_role = self.context.players[target_seat].role.value
                announcement_text = f"☠️ 女巫 ({player_seat}号) 使用毒药毒杀了 {target_seat}号 ({target_role})"
            else:
                if self.context.witch_context:
                    self.context.witch_context['has_poison_potion'] = False
                announcement_text = f"☠️ 女巫 ({player_seat}号) 选择不使用毒药"
        else:
            return False, "Invalid action type", None

        # 记录角色已完成行动
        if role not in self.context.night_actions_completed:
            self.context.night_actions_completed.append(role)

        # 角色行动完成，推进到下一个角色或结束晚上阶段
        next_role = self._get_next_night_role(role)
        if next_role:
            self.context.night_current_role = next_role
            # 播报给当前角色
            self._announce_night_role_action(next_role, announcement_text)
        else:
            # 所有人都行动完成，转换到新一天
            self.transition_to('day_discussion')

        return True, "Night action submitted successfully", {
            'action': action_type,
            'targetSeat': target_seat,
            'announcement': announcement_text
        }

    def _get_next_night_role(self, current_role: str) -> Optional[str]:
        """获取下一个需要行动的角色"""
        role_order = ['seer', 'werewolf', 'witch']
        for role in role_order:
            if role not in self.context.night_actions_completed:
                return role
        return None

    def _announce_night_role_action(self, role: str, announcement_text: Optional[str]):
        """播报当前角色的行动任务"""
        if not announcement_text:
            return

        # 设置播报内容到扩展字段（不影响游戏状态）
        from datetime import datetime
        self.context.extensions['announcement'] = announcement_text
        self.context.extensions['announcement_time'] = datetime.now().timestamp()
        self.context.extensions['action_role'] = role  # 记录播报给谁

    def _handle_advance_speaker(self, payload: Dict) -> Tuple[bool, str, Any]:
        """
        处理推进发言者动作

        参数:
            payload: {}
        """
        if not self.context.speaking_order:
            return False, "No speaking order available", None

        next_index = self.context.current_speaker_index + 1
        if next_index >= len(self.context.speaking_order):
            # 所有人都发言完了，自动转换到投票阶段（会触发播报）
            self.transition_to('day_voting')
            return True, "All speakers finished, moving to voting", None

        self.context.current_speaker_index = next_index
        self.context.speaking_start_time = __import__('datetime').datetime.now().timestamp()

        return True, "Speaker advanced successfully", {
            'currentSpeaker': self.context.speaking_order[next_index]
        }

    # === 内部方法 ===

    def _init_speaking_order(self):
        """初始化发言顺序"""
        from datetime import datetime
        self.context.speaking_order = self.context.get_alive_players()
        self.context.current_speaker_index = 0
        self.context.speaking_start_time = datetime.now().timestamp()

    def advance_speaker(self) -> bool:
        """
        推进到下一个发言者
        返回: 是否成功推进
        """
        success, message, data = self._handle_advance_speaker({})
        return success

    def _init_voting(self):
        """初始化投票"""
        from datetime import datetime
        # 重置所有玩家的投票状态
        for player in self.context.players.values():
            player.has_voted = False
            player.voted_for = None

        self.context.voting_start_time = datetime.now().timestamp()
        self.context.voting_voted_count = 0
        self.context.voting_result = None

    def agent_vote(self, seat: int) -> Tuple[bool, str, Any]:
        """
        让 Agent 投票

        参数:
            seat: Agent 的座位号

        返回:
            (success, message, result)
        """
        if seat not in self.context.players:
            return False, "Invalid player seat", None

        player = self.context.players[seat]

        if not player.alive:
            return False, "Player is not alive", None

        if player.has_voted:
            return False, "Already voted", None

        # 使用智能决策系统
        from agent_decision import decide_agent_vote

        # 获取可选目标
        alive_players = self.context.get_alive_players()
        available_targets = [s for s in alive_players if s != seat]

        if not available_targets:
            return False, "No available targets", None

        # 让 Agent 做出投票决策
        decision = decide_agent_vote(self.room_id, seat, available_targets, self.context)

        # 调用统一的投票处理器，确保逻辑一致
        return self._handle_vote({
            'voterSeat': decision['voterSeat'],
            'targetSeat': decision['targetSeat']
        })

    def _calculate_voting_result(self):
        """计算投票结果"""
        # 记录详细投票信息：谁投了谁
        vote_details = []
        vote_counts = {}

        for seat, player in self.context.players.items():
            if player.alive and player.voted_for:
                target = player.voted_for
                vote_details.append({
                    'voter': seat,
                    'target': target
                })
                # 统计每个目标的票数
                vote_counts[target] = vote_counts.get(target, 0) + 1

        if not vote_details:
            self.context.voting_result = {
                'voted_out': None,
                'vote_counts': {},
                'vote_details': []
            }
            return

        # 找出票数最多的玩家
        max_votes = max(vote_counts.values())
        voted_outs = [seat for seat, count in vote_counts.items() if count == max_votes]

        # 平票处理：随机选择
        voted_out = random.choice(voted_outs) if len(voted_outs) > 1 else voted_outs[0]

        # 构建投票结果播报文本
        announcement_lines = ['🗳️ 投票结果：']
        for detail in vote_details:
            voter = detail['voter']
            target = detail['target']
            announcement_lines.append(f'  {voter}号 ➡️ {target}号')

        if voted_out:
            announcement_lines.append(f'\n💀 {voted_out}号玩家被投票出局（{vote_counts[voted_out]}票）')
        else:
            announcement_lines.append(f'\n⚠️ 无人被投票出局')

        announcement_text = '\n'.join(announcement_lines)

        self.context.voting_result = {
            'voted_out': voted_out,
            'vote_counts': vote_counts,
            'vote_details': vote_details  # 详细投票记录
        }

        # 设置播报内容到扩展字段（不影响游戏状态）
        from datetime import datetime
        self.context.extensions['announcement'] = announcement_text
        self.context.extensions['announcement_time'] = datetime.now().timestamp()

    def _execute_voting(self):
        """执行白天投票逻辑"""
        if not self.context.voting_result:
            return

        voted_out = self.context.voting_result.get('voted_out')
        vote_counts = self.context.voting_result.get('vote_counts', {})

        if voted_out and voted_out in self.context.players:
            player = self.context.players[voted_out]
            player.alive = False
            self.context.vote_count[voted_out] = vote_counts.get(voted_out, 0)

            # 记录昨晚死亡信息
            self.context.last_dead_player = {
                'seat': voted_out,
                'role': player.role.value,
                'killed_by': KilledBy.VOTE.value
            }

            self._add_message('player_death', {
                'seat': voted_out,
                'role': player.role.value,
                'killed_by': KilledBy.VOTE.value,
                'round': self.context.round
            })

    def _execute_night_actions(self):
        """执行晚上行动逻辑"""
        # 狼人的杀戮
        killed = self.context.werewolf_killed

        # 女巫的救援
        saved = self.context.witch_saved

        # 女巫的毒杀
        poisoned = self.context.witch_poisoned

        # 如果女巫救了被杀的人，则该人活着
        if killed and saved == killed:
            # 被救了，不死
            pass
        elif killed and killed in self.context.players:
            # 被狼人杀死
            player = self.context.players[killed]
            player.alive = False

            # 记录昨晚死亡信息
            self.context.last_dead_player = {
                'seat': killed,
                'role': player.role.value,
                'killed_by': KilledBy.WEREWOLF.value
            }

            self._add_message('player_death', {
                'seat': killed,
                'role': player.role.value,
                'killed_by': KilledBy.WEREWOLF.value,
                'round': self.context.round
            })

        # 女巫的毒杀
        if poisoned and poisoned != killed and poisoned in self.context.players:
            player = self.context.players[poisoned]
            player.alive = False

            # 记录昨晚死亡信息（如果狼人没杀人的话，女巫毒杀的人就是昨晚死亡）
            self.context.last_dead_player = {
                'seat': poisoned,
                'role': player.role.value,
                'killed_by': KilledBy.WITCH.value
            }

            self._add_message('player_death', {
                'seat': poisoned,
                'role': player.role.value,
                'killed_by': KilledBy.WITCH.value,
                'round': self.context.round
            })

        # 重置夜间行动
        self.context.witch_saved = None
        self.context.witch_poisoned = None
        self.context.werewolf_killed = None
        self.context.seer_checked = None

    def _check_game_over(self) -> bool:
        """检查游戏是否结束"""
        alive_players = [p for p in self.context.players.values() if p.alive]
        alive_werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        alive_villagers = [p for p in alive_players if p.role != Role.WEREWOLF]

        # 狼人全死 -> 村民获胜
        if not alive_werewolves:
            self.context.result = GameResult.VILLAGER_WIN.value
            self._add_message('game_end', {
                'winner': 'villager',
                'round': self.context.round
            })
            return True

        # 狼人数 >= 村民数 -> 狼人获胜
        if len(alive_werewolves) >= len(alive_villagers):
            self.context.result = GameResult.WEREWOLF_WIN.value
            self._add_message('game_end', {
                'winner': 'werewolf',
                'round': self.context.round
            })
            return True

        return False

    def _get_extended_state(self) -> Dict[str, Any]:
        """获取经典狼人杀的扩展状态"""
        from datetime import datetime

        extended_state = {}

        # 如果在发言阶段，返回发言相关信息
        if self.context.phase == 'day_discussion':
            current_speaker = None
            if self.context.speaking_order and self.context.current_speaker_index < len(self.context.speaking_order):
                current_speaker = self.context.speaking_order[self.context.current_speaker_index]

            elapsed_time = datetime.now().timestamp() - self.context.speaking_start_time
            time_left = max(0, 60 - int(elapsed_time))  # 60秒发言时间

            extended_state.update({
                'speakingOrder': self.context.speaking_order,
                'currentSpeaker': current_speaker,
                'currentSpeakerIndex': self.context.current_speaker_index,
                'speakingTimeLeft': time_left
            })

        # 如果在投票阶段，返回投票相关信息
        elif self.context.phase == 'day_voting':
            elapsed_time = datetime.now().timestamp() - self.context.voting_start_time
            time_left = max(0, 20 - int(elapsed_time))  # 20秒投票时间

            extended_state.update({
                'votingTimeLeft': time_left,
                'votingVotedCount': self.context.voting_voted_count,
                'votingResult': self.context.voting_result
            })

            # 返回每个玩家的投票状态
            player_votes = {}
            for seat, player in self.context.players.items():
                if player.alive:
                    player_votes[seat] = {
                        'hasVoted': player.has_voted,
                        'votedFor': player.voted_for
                    }
            extended_state['playerVotes'] = player_votes

        # 如果在晚上行动阶段，返回晚上行动相关信息
        elif self.context.phase == 'night_action':
            # 计算当前角色行动时间
            elapsed_time = datetime.now().timestamp() - self.context.night_action_start_time
            time_left = max(0, 60 - int(elapsed_time))  # 60秒行动时间

            # 如果超时，自动推进到下一个角色
            if time_left <= 0 and self.context.night_current_role:
                current_role = self.context.night_current_role
                next_role = self._get_next_night_role(current_role)
                if next_role:
                    self.context.night_current_role = next_role
                    self.context.night_action_start_time = datetime.now().timestamp()
                else:
                    # 所有人都行动完成，转换到新一天
                    self.transition_to('day_discussion')

            extended_state.update({
                'currentRole': self.context.night_current_role,
                'nightTimeLeft': time_left,
                'nightActionsCompleted': self.context.night_actions_completed
            })

        return extended_state

