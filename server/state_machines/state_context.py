"""
状态上下文
定义游戏状态的通用数据容器，跨模式共享
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .state_enums import Role


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
class GameStateContext:
    """
    游戏状态上下文 - 跨模式共享
    所有游戏模式共享的基础状态
    """
    room_id: str
    mode: str  # 'classic', 'quick', etc.
    phase: str = 'waiting'
    result: str = 'ongoing'
    round: int = 0

    # 玩家数据
    players: Dict[int, Player] = field(default_factory=dict)
    messages: List[GameMessage] = field(default_factory=list)

    # 时间管理
    phase_start_time: float = 0.0
    phase_duration: int = 0

    # 夜间行动（经典模式）
    witch_saved: Optional[int] = None
    witch_poisoned: Optional[int] = None
    werewolf_killed: Optional[int] = None
    seer_checked: Optional[int] = None

    # 昨晚死亡信息
    last_dead_player: Optional[Dict] = None  # {'seat', 'role', 'killed_by'}

    # 晚上行动状态管理
    night_current_role: Optional[str] = None  # 当前行动的角色：'seer', 'werewolf', 'witch'
    night_action_start_time: float = 0.0  # 当前角色行动开始时间
    night_actions_completed: List[str] = field(default_factory=list)  # 已完成行动的角色列表

    # 投票数据（经典模式）
    vote_count: Dict[int, int] = field(default_factory=dict)

    # 发言相关（经典模式）
    speaking_order: List[int] = field(default_factory=list)
    current_speaker_index: int = 0
    speaking_start_time: float = 0.0

    # 投票相关（经典模式）
    voting_start_time: float = 0.0
    voting_voted_count: int = 0
    voting_result: Optional[Dict] = None

    # 角色特定上下文（用于 Agent 决策）
    werewolf_context: Optional[Dict] = None  # 狼人队友信息
    seer_context: Optional[List[Dict]] = None  # 预言家查验历史
    witch_context: Optional[Dict] = None  # 女巫药水状态

    # 扩展字段 - 用于特定模式的额外数据
    extensions: Dict[str, Any] = field(default_factory=dict)

    def get_alive_players(self) -> List[int]:
        """获取存活玩家座位号列表"""
        return [p.seat for p in self.players.values() if p.alive]

    def get_dead_players(self) -> List[int]:
        """获取死亡玩家座位号列表"""
        return [p.seat for p in self.players.values() if not p.alive]

    def get_player_by_seat(self, seat: int) -> Optional[Player]:
        """根据座位号获取玩家"""
        return self.players.get(seat)

