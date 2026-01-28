"""
状态机工厂
负责根据游戏模式创建对应的状态机实例
"""
from typing import Dict, Type

from .base_state_machine import BaseStateMachine
from .classic_werewolf_state_machine import ClassicWerewolfStateMachine
from .state_enums import GameMode

# 注册的状态机类型
_STATE_MACHINE_REGISTRY: Dict[str, Type[BaseStateMachine]] = {
    GameMode.CLASSIC.value: ClassicWerewolfStateMachine,
    # 可以在这里注册其他游戏模式的状态机
    # GameMode.QUICK.value: QuickModeStateMachine,
    # GameMode.ADVANCED.value: AdvancedWerewolfStateMachine,
}


def create_state_machine(
    room_id: str,
    mode: str = GameMode.CLASSIC.value,
    seat_count: int = 12
) -> BaseStateMachine:
    """
    创建状态机实例

    参数:
        room_id: 房间ID
        mode: 游戏模式（默认为经典模式）
        seat_count: 座位数（默认为12人局）

    返回:
        状态机实例

    异常:
        ValueError: 如果不支持的游戏模式
    """
    if mode not in _STATE_MACHINE_REGISTRY:
        raise ValueError(f"Unsupported game mode: {mode}")

    state_machine_class = _STATE_MACHINE_REGISTRY[mode]

    # 根据不同的状态机类型，可能需要不同的初始化参数
    if mode == GameMode.CLASSIC.value:
        return state_machine_class(room_id, seat_count)
    else:
        return state_machine_class(room_id, seat_count)


def register_state_machine(mode: str, state_machine_class: Type[BaseStateMachine]):
    """
    注册新的状态机类型
    用于扩展新的游戏模式

    参数:
        mode: 游戏模式名称
        state_machine_class: 状态机类
    """
    _STATE_MACHINE_REGISTRY[mode] = state_machine_class


def get_supported_modes() -> list:
    """获取所有支持的游戏模式"""
    return list(_STATE_MACHINE_REGISTRY.keys())

