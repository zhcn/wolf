"""
游戏引擎（重构版）
使用状态机架构管理游戏逻辑
"""
from typing import Dict, Optional

from state_machines import (
    create_state_machine,
    BaseStateMachine,
    GameStateContext,
    ClassicWerewolfStateMachine
)


class GameEngine:
    """
    游戏引擎 - 管理游戏实例和状态机

    负责创建和管理游戏房间的状态机实例，
    提供统一的接口供路由层调用
    """

    def __init__(self, room_id: str, mode: str = 'classic', seat_count: int = 12):
        """
        初始化游戏引擎

        参数:
            room_id: 房间ID
            mode: 游戏模式（默认为经典模式）
            seat_count: 座位数
        """
        self.room_id = room_id
        self.mode = mode
        self.seat_count = seat_count

        # 创建状态机实例
        self.state_machine: BaseStateMachine = create_state_machine(
            room_id=room_id,
            mode=mode,
            seat_count=seat_count
        )

    def assign_roles(self) -> Dict[int, str]:
        """
        分配角色

        返回:
            {座位号: 角色名称}
        """
        if isinstance(self.state_machine, ClassicWerewolfStateMachine):
            return self.state_machine.assign_roles()
        else:
            raise NotImplementedError(f"assign_roles not implemented for mode: {self.mode}")

    def start_round(self) -> tuple:
        """
        推进游戏到下一阶段

        返回:
            (阶段名称, 持续时间秒数)
        """
        if isinstance(self.state_machine, ClassicWerewolfStateMachine):
            return self.state_machine.start_round()
        else:
            raise NotImplementedError(f"start_round not implemented for mode: {self.mode}")

    def submit_vote(self, voter_seat: int, target_seat: int) -> bool:
        """
        提交投票

        参数:
            voter_seat: 投票者座位
            target_seat: 目标座位

        返回:
            是否成功
        """
        success, message, _ = self.state_machine.handle_player_action(
            'vote',
            {'voterSeat': voter_seat, 'targetSeat': target_seat}
        )
        return success

    def submit_speech(self, seat: int, text: str) -> bool:
        """
        提交发言

        参数:
            seat: 发言者座位
            text: 发言内容

        返回:
            是否成功
        """
        success, message, _ = self.state_machine.handle_player_action(
            'speech',
            {'seat': seat, 'text': text}
        )
        return success

    def submit_night_action(self, player_seat: int, role: str,
                           action_type: str, target_seat: Optional[int] = None) -> bool:
        """
        提交晚上行动

        参数:
            player_seat: 玩家座位
            role: 角色
            action_type: 动作类型
            target_seat: 目标座位（可选）

        返回:
            是否成功
        """
        success, message, _ = self.state_machine.handle_player_action(
            'night_action',
            {
                'playerSeat': player_seat,
                'role': role,
                'actionType': action_type,
                'targetSeat': target_seat
            }
        )
        return success

    def advance_speaker(self) -> bool:
        """
        推进到下一个发言者

        返回:
            是否成功推进
        """
        if isinstance(self.state_machine, ClassicWerewolfStateMachine):
            return self.state_machine.advance_speaker()
        else:
            raise NotImplementedError(f"advance_speaker not implemented for mode: {self.mode}")

    def agent_vote(self, seat: int) -> tuple:
        """
        让 Agent 投票

        参数:
            seat: Agent 的座位号

        返回:
            (success, message, result)
        """
        if isinstance(self.state_machine, ClassicWerewolfStateMachine):
            return self.state_machine.agent_vote(seat)
        else:
            raise NotImplementedError(f"agent_vote not implemented for mode: {self.mode}")

    def get_state(self) -> Dict:
        """
        获取当前游戏状态

        返回:
            游戏状态字典（使用 camelCase）
        """
        return self.state_machine.get_state_for_frontend()

    def complete_announcement(self) -> bool:
        """
        完成播报，转换到待定阶段

        返回:
            是否成功
        """
        return self.state_machine.complete_announcement()

    def get_messages(self) -> list:
        """
        获取游戏消息列表

        返回:
            消息列表
        """
        messages = []
        for msg in self.state_machine.context.messages:
            messages.append({
                'id': msg.id,
                'timestamp': msg.timestamp,
                'type': msg.type,
                'content': msg.content
            })
        return messages

    @property
    def game_state(self) -> GameStateContext:
        """获取游戏状态上下文"""
        return self.state_machine.context


# 全局游戏实例管理
_game_instances: Dict[str, GameEngine] = {}


def get_or_create_game(room_id: str, mode: str = 'classic', seat_count: int = 12) -> GameEngine:
    """
    获取或创建游戏实例

    参数:
        room_id: 房间ID
        mode: 游戏模式
        seat_count: 座位数

    返回:
        游戏引擎实例
    """
    if room_id not in _game_instances:
        _game_instances[room_id] = GameEngine(room_id, mode, seat_count)
    return _game_instances[room_id]


def get_game(room_id: str) -> Optional[GameEngine]:
    """
    获取游戏实例

    参数:
        room_id: 房间ID

    返回:
        游戏引擎实例，如果不存在则返回 None
    """
    return _game_instances.get(room_id)


def remove_game(room_id: str) -> bool:
    """
    移除游戏实例

    参数:
        room_id: 房间ID

    返回:
        是否成功移除
    """
    if room_id in _game_instances:
        del _game_instances[room_id]
        return True
    return False

