"""
状态机模块
提供可扩展的游戏状态机框架
"""
from .base_state_machine import BaseStateMachine
from .classic_werewolf_state_machine import ClassicWerewolfStateMachine
from .state_context import GameStateContext, Player, GameMessage
from .state_enums import GameMode, Role, GameResult, KilledBy
from .state_machine_factory import create_state_machine, register_state_machine, get_supported_modes

__all__ = [
    # 枚举
    'GameMode',
    'Role',
    'GameResult',
    'KilledBy',
    # 上下文
    'GameStateContext',
    'Player',
    'GameMessage',
    # 基类
    'BaseStateMachine',
    # 具体实现
    'ClassicWerewolfStateMachine',
    # 工厂
    'create_state_machine',
    'register_state_machine',
    'get_supported_modes',
]

