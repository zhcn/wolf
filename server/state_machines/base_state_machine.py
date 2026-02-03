"""
状态机基类
定义所有状态机的通用接口和核心功能
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Tuple, Optional, Any

from .state_context import GameStateContext

logger = logging.getLogger('state_machine')


class BaseStateMachine(ABC):
    """
    状态机基类 - 定义核心接口
    所有游戏模式的状态机都继承自这个基类
    """

    def __init__(self, room_id: str, mode: str, context: GameStateContext):
        self.room_id = room_id
        self.mode = mode
        self.context = context

        # 阶段转换规则：{当前阶段: {next_phase: 下一阶段, duration: 持续时间}}
        self._phase_transitions: Dict[str, Dict[str, Any]] = {}

        # 阶段处理器：{阶段名: 处理函数}
        self._phase_handlers: Dict[str, callable] = {}

        # 玩家动作处理器：{动作名: 处理函数}
        self._action_handlers: Dict[str, callable] = {}

        # 初始化该模式的所有阶段和动作处理器
        self.initialize()

    @abstractmethod
    def initialize(self) -> None:
        """
        初始化状态机
        子类必须实现此方法，设置：
        - 阶段转换规则
        - 阶段处理器
        - 动作处理器
        """
        pass

    def get_next_phase(self, current_phase: str) -> Tuple[str, int]:
        """
        获取下一个阶段和持续时间

        参数:
            current_phase: 当前阶段

        返回:
            (下一阶段名称, 持续时间秒数)
        """
        if current_phase in self._phase_transitions:
            transition = self._phase_transitions[current_phase]
            next_phase = transition.get('next_phase', 'waiting')
            duration = transition.get('duration', 0)
            return next_phase, duration
        return 'waiting', 0

    def transition_to(self, next_phase: str) -> bool:
        """
        转换到指定阶段

        参数:
            next_phase: 目标阶段

        返回:
            是否转换成功
        """
        # 直接进入下一阶段
        self.context.phase = next_phase
        self.context.phase_start_time = datetime.now().timestamp()

        # 获取阶段持续时间
        if next_phase in self._phase_transitions:
            self.context.phase_duration = self._phase_transitions[next_phase].get('duration', 0)

        # 检查是否有播报内容
        announcement_content = self._get_phase_announcement(next_phase)
        if announcement_content:
            # 设置播报信息（附加信息，不影响游戏状态）
            self.context.extensions['announcement'] = announcement_content
            self.context.extensions['announcement_time'] = datetime.now().timestamp()
        else:
            # 清除播报信息
            self.context.extensions.pop('announcement', None)
            self.context.extensions.pop('announcement_time', None)

        # 调用阶段初始化处理器
        if next_phase in self._phase_handlers:
            self._phase_handlers[next_phase]()

        # 添加阶段变更消息
        self._add_message('phase_change', {
            'phase': next_phase,
            'round': self.context.round
        })

        return True


    def _get_phase_announcement(self, phase: str) -> str:
        """
        获取阶段转换的播报内容

        参数:
            phase: 阶段名称

        返回:
            播报内容文本
        """
        phase_texts = {
            'waiting': '🏠 游戏准备阶段 - 等待玩家加入...',
            'role_assigned': '🎭 角色分配完成！请查看你的角色信息',
            'day_discussion': '💬 白天讨论阶段开始 - 请大家轮流发言',
            'day_voting': '🗳️ 白天投票阶段开始 - 请投票选出要驱逐的玩家',
            'night_action': '🌙 晚上行动阶段 - 请各位根据角色执行夜间行动',
            'game_over': '🎊 游戏结束！感谢大家的参与'
        }
        return phase_texts.get(phase, f'⏭️ 游戏进入{phase}阶段')

    def handle_player_action(self, action: str, payload: Dict) -> Tuple[bool, str, Any]:
        """
        处理玩家动作

        参数:
            action: 动作名称（如 'vote', 'speech', 'night_action'）
            payload: 动作数据

        返回:
            (是否成功, 消息, 数据)
        """
        if action not in self._action_handlers:
            return False, f"Unknown action: {action}", None

        handler = self._action_handlers[action]
        try:
            success, message, data = handler(payload)
            return success, message, data
        except Exception as e:
            return False, str(e), None

    def get_state_for_frontend(self) -> Dict[str, Any]:
        """
        获取前端需要的状态（统一格式）
        子类可以重写此方法添加特定字段

        返回:
            状态字典（使用 camelCase）
        """
        # 计算阶段剩余时间
        phase_time_left = 0
        if self.context.phase_start_time > 0 and self.context.phase_duration > 0:
            elapsed = datetime.now().timestamp() - self.context.phase_start_time
            phase_time_left = max(0, self.context.phase_duration - int(elapsed))

        base_state = {
            'mode': self.mode,
            'roomId': self.room_id,
            'phase': self.context.phase,
            'result': self.context.result,
            'round': self.context.round,
            'alivePlayers': self.context.get_alive_players(),
            'deadPlayers': self.context.get_dead_players(),
            'phaseTimeLeft': phase_time_left,
        }

        # 如果有播报信息，返回播报内容（不影响游戏状态）
        if 'announcement' in self.context.extensions:
            announcement_time = self.context.extensions.get('announcement_time', 0)
            # 播报只显示 5 秒后自动清除
            if announcement_time and (datetime.now().timestamp() - announcement_time) < 5:
                base_state['announcement'] = self.context.extensions['announcement']
            else:
                # 超时清除播报信息
                self.context.extensions.pop('announcement', None)
                self.context.extensions.pop('announcement_time', None)

        # 子类扩展字段
        extended_state = self._get_extended_state()
        logger.debug(f"[base_state_machine] extended_state: {extended_state}, phase: {self.context.phase}")

        return {**base_state, **extended_state}

    def _get_extended_state(self) -> Dict[str, Any]:
        """
        获取扩展状态
        子类可以重写此方法添加特定模式的状态字段

        返回:
            扩展状态字典
        """
        return {}

    def _add_message(self, msg_type: str, content: Dict):
        """添加游戏消息"""
        msg_id = f"{int(datetime.now().timestamp() * 1000)}"
        from .state_context import GameMessage
        message = GameMessage(
            id=msg_id,
            timestamp=datetime.now().timestamp(),
            type=msg_type,
            content=content
        )
        self.context.messages.append(message)

    def _register_phase_transition(self, phase: str, next_phase: str, duration: int,
                                   handler: Optional[callable] = None):
        """
        注册阶段转换规则

        参数:
            phase: 当前阶段
            next_phase: 下一阶段
            duration: 当前阶段持续时间
            handler: 进入下一阶段时的处理器（可选）
        """
        self._phase_transitions[phase] = {
            'next_phase': next_phase,
            'duration': duration
        }
        if handler:
            self._phase_handlers[next_phase] = handler

    def _register_action_handler(self, action: str, handler: callable):
        """
        注册动作处理器

        参数:
            action: 动作名称
            handler: 处理函数
        """
        self._action_handlers[action] = handler

