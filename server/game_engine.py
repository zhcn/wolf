"""
狼人杀游戏引擎
处理游戏规则、角色分配、阶段流转、投票等核心逻辑
"""
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Role(Enum):
    """角色类型"""
    WEREWOLF = 'werewolf'    # 狼人
    VILLAGER = 'villager'    # 村民
    SEER = 'seer'            # 预言家
    WITCH = 'witch'          # 女巫
    HUNTER = 'hunter'        # 猎人

class GamePhase(Enum):
    """游戏阶段"""
    WAITING = 'waiting'              # 等待开始
    ROLE_ASSIGNED = 'role_assigned'  # 角色已分配
    DAY_DISCUSSION = 'day_discussion' # 白天讨论
    DAY_VOTING = 'day_voting'         # 白天投票
    NIGHT_ACTION = 'night_action'     # 晚上行动
    DAY_RESULT = 'day_result'         # 白天投票结果
    NIGHT_RESULT = 'night_result'     # 晚上行动结果
    GAME_OVER = 'game_over'           # 游戏结束

class GameResult(Enum):
    """游戏结果"""
    ONGOING = 'ongoing'
    WEREWOLF_WIN = 'werewolf_win'
    VILLAGER_WIN = 'villager_win'

class KilledBy(Enum):
    """死亡原因"""
    VOTE = 'vote'              # 投票驱逐
    WEREWOLF = 'werewolf'      # 狼人杀死
    WITCH = 'witch'            # 女巫毒死

@dataclass
class Player:
    """玩家信息"""
    seat: int
    role: Optional[Role] = None
    alive: bool = True
    has_voted: bool = False
    voted_for: Optional[int] = None

@dataclass
class GameMessage:
    """游戏事件消息"""
    id: str
    timestamp: float
    type: str  # 'phase_change', 'player_death', 'vote_result', 'game_end'
    content: Dict

@dataclass
class GameState:
    """游戏状态"""
    room_id: str
    phase: GamePhase = GamePhase.WAITING
    result: GameResult = GameResult.ONGOING
    round: int = 0
    players: Dict[int, Player] = field(default_factory=dict)
    messages: List[GameMessage] = field(default_factory=list)

    # 夜间行动
    witch_saved: Optional[int] = None  # 女巫救了谁
    witch_poisoned: Optional[int] = None  # 女巫毒死谁
    werewolf_killed: Optional[int] = None  # 狼人杀死谁
    seer_checked: Optional[int] = None  # 预言家检查谁

    # 投票数据
    vote_count: Dict[int, int] = field(default_factory=dict)

class GameEngine:
    """狼人杀游戏引擎"""

    # 12人局的默认角色配置
    DEFAULT_ROLES_12P = [
        Role.WEREWOLF, Role.WEREWOLF,  # 2 个狼人
        Role.SEER, Role.WITCH, Role.HUNTER,  # 特殊角色
        Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,  # 7 个村民
        Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER
    ]

    def __init__(self, room_id: str, seat_count: int = 12):
        """初始化游戏引擎"""
        self.room_id = room_id
        self.seat_count = seat_count
        self.game_state = GameState(room_id=room_id)
        self._init_players()

    def _init_players(self):
        """初始化玩家对象"""
        for seat in range(1, self.seat_count + 1):
            self.game_state.players[seat] = Player(seat=seat)

    def assign_roles(self) -> Dict[int, str]:
        """
        分配角色
        返回: {seat: role_name}
        """
        # 获取角色池
        if self.seat_count == 12:
            roles = self.DEFAULT_ROLES_12P.copy()
        else:
            # 自定义座位数的角色配置
            roles = self._get_custom_roles(self.seat_count)

        # 随机洗牌
        random.shuffle(roles)

        # 为每个玩家分配角色
        for seat, role in enumerate(roles, start=1):
            self.game_state.players[seat].role = role

        # 更新游戏状态
        self.game_state.phase = GamePhase.ROLE_ASSIGNED
        self.game_state.round = 1

        # 返回座位-角色映射
        return {
            seat: player.role.value
            for seat, player in self.game_state.players.items()
        }

    def _get_custom_roles(self, count: int) -> List[Role]:
        """根据玩家数获取自定义角色配置"""
        # 可以根据玩家数调整角色数量
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
        """
        推进游戏到下一阶段
        返回: (阶段名称, 持续时间秒)
        """
        current_phase = self.game_state.phase

        if current_phase == GamePhase.ROLE_ASSIGNED:
            next_phase = GamePhase.DAY_DISCUSSION
            duration = 120  # 白天讨论 2 分钟
        elif current_phase == GamePhase.DAY_DISCUSSION:
            next_phase = GamePhase.DAY_VOTING
            duration = 60   # 白天投票 1 分钟
        elif current_phase == GamePhase.DAY_VOTING:
            # 执行投票驱逐逻辑
            self._execute_voting()
            next_phase = GamePhase.NIGHT_ACTION
            duration = 120  # 晚上行动 2 分钟
        elif current_phase == GamePhase.NIGHT_ACTION:
            # 执行晚上行动逻辑
            self._execute_night_actions()
            # 检查游戏是否结束
            if self._check_game_over():
                next_phase = GamePhase.GAME_OVER
                duration = 0
            else:
                self.game_state.round += 1
                next_phase = GamePhase.DAY_DISCUSSION
                duration = 120
        else:
            next_phase = GamePhase.WAITING
            duration = 0

        self.game_state.phase = next_phase
        self._add_message('phase_change', {
            'from': current_phase.value,
            'to': next_phase.value,
            'round': self.game_state.round
        })

        return next_phase.value, duration

    def _execute_voting(self):
        """执行白天投票逻辑"""
        # 统计投票
        votes = {}
        for seat, player in self.game_state.players.items():
            if player.alive and player.voted_for:
                target = player.voted_for
                votes[target] = votes.get(target, 0) + 1

        if not votes:
            return

        # 找出票数最多的玩家
        max_votes = max(votes.values())
        voted_outs = [seat for seat, count in votes.items() if count == max_votes]

        # 平票处理：随机选择
        if len(voted_outs) > 1:
            voted_out = random.choice(voted_outs)
        else:
            voted_out = voted_outs[0]

        # 驱逐玩家
        if voted_out in self.game_state.players:
            player = self.game_state.players[voted_out]
            player.alive = False
            self.game_state.vote_count[voted_out] = votes[voted_out]

            self._add_message('player_death', {
                'seat': voted_out,
                'role': player.role.value,
                'killed_by': KilledBy.VOTE.value,
                'round': self.game_state.round
            })

    def _execute_night_actions(self):
        """执行晚上行动逻辑"""
        # 狼人的杀戮
        killed = self.game_state.werewolf_killed

        # 女巫的救援
        saved = self.game_state.witch_saved

        # 女巫的毒杀
        poisoned = self.game_state.witch_poisoned

        # 如果女巫救了被杀的人，则该人活着
        if killed and saved == killed:
            # 被救了，不死
            pass
        elif killed:
            # 被狼人杀死
            if killed in self.game_state.players:
                player = self.game_state.players[killed]
                player.alive = False
                self._add_message('player_death', {
                    'seat': killed,
                    'role': player.role.value,
                    'killed_by': KilledBy.WEREWOLF.value,
                    'round': self.game_state.round
                })

        # 女巫的毒杀
        if poisoned and poisoned != killed:
            if poisoned in self.game_state.players:
                player = self.game_state.players[poisoned]
                player.alive = False
                self._add_message('player_death', {
                    'seat': poisoned,
                    'role': player.role.value,
                    'killed_by': KilledBy.WITCH.value,
                    'round': self.game_state.round
                })

        # 重置夜间行动
        self.game_state.witch_saved = None
        self.game_state.witch_poisoned = None
        self.game_state.werewolf_killed = None
        self.game_state.seer_checked = None

    def _check_game_over(self) -> bool:
        """
        检查游戏是否结束
        返回: 游戏是否结束
        """
        alive_players = [p for p in self.game_state.players.values() if p.alive]
        alive_werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        alive_villagers = [p for p in alive_players if p.role != Role.WEREWOLF]

        # 狼人全死 -> 村民获胜
        if not alive_werewolves:
            self.game_state.result = GameResult.VILLAGER_WIN
            self._add_message('game_end', {
                'winner': 'villager',
                'round': self.game_state.round
            })
            return True

        # 狼人数 >= 村民数 -> 狼人获胜
        if len(alive_werewolves) >= len(alive_villagers):
            self.game_state.result = GameResult.WEREWOLF_WIN
            self._add_message('game_end', {
                'winner': 'werewolf',
                'round': self.game_state.round
            })
            return True

        return False

    def submit_vote(self, voter_seat: int, target_seat: int) -> bool:
        """
        提交投票
        返回: 是否成功
        """
        if voter_seat not in self.game_state.players or target_seat not in self.game_state.players:
            return False

        voter = self.game_state.players[voter_seat]
        if not voter.alive:
            return False

        target = self.game_state.players[target_seat]
        if not target.alive:
            return False

        voter.voted_for = target_seat
        voter.has_voted = True
        return True

    def submit_night_action(self, player_seat: int, role: str, action_type: str,
                           target_seat: Optional[int] = None) -> bool:
        """
        提交晚上行动
        返回: 是否成功
        """
        player = self.game_state.players.get(player_seat)
        if not player or not player.alive:
            return False

        if player.role.value != role:
            return False

        if action_type == 'kill' and role == 'werewolf':
            self.game_state.werewolf_killed = target_seat
            return True
        elif action_type == 'check' and role == 'seer':
            self.game_state.seer_checked = target_seat
            return True
        elif action_type == 'save' and role == 'witch':
            self.game_state.witch_saved = target_seat
            return True
        elif action_type == 'poison' and role == 'witch':
            self.game_state.witch_poisoned = target_seat
            return True

        return False

    def get_state(self) -> Dict:
        """
        获取当前游戏状态
        返回: 游戏状态字典
        """
        alive_players = [p.seat for p in self.game_state.players.values() if p.alive]
        dead_players = [p.seat for p in self.game_state.players.values() if not p.alive]

        return {
            'room_id': self.room_id,
            'phase': self.game_state.phase.value,
            'result': self.game_state.result.value,
            'round': self.game_state.round,
            'alive_players': alive_players,
            'dead_players': dead_players,
        }

    def _add_message(self, msg_type: str, content: Dict):
        """添加游戏消息"""
        msg_id = f"{int(datetime.now().timestamp() * 1000)}"
        message = GameMessage(
            id=msg_id,
            timestamp=datetime.now().timestamp(),
            type=msg_type,
            content=content
        )
        self.game_state.messages.append(message)


# 全局游戏实例管理
game_instances: Dict[str, GameEngine] = {}

def get_or_create_game(room_id: str, seat_count: int = 12) -> GameEngine:
    """获取或创建游戏实例"""
    if room_id not in game_instances:
        game_instances[room_id] = GameEngine(room_id, seat_count)
    return game_instances[room_id]

def get_game(room_id: str) -> Optional[GameEngine]:
    """获取游戏实例"""
    return game_instances.get(room_id)

