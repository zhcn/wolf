"""
状态机枚举定义
定义游戏模式、角色、通用状态等枚举
"""
from enum import Enum


class GameMode(str, Enum):
    """游戏模式"""
    CLASSIC = 'classic'           # 经典狼人杀
    QUICK = 'quick'               # 快速模式
    ADVANCED = 'advanced'         # 高级规则


class Role(str, Enum):
    """角色类型"""
    WEREWOLF = 'werewolf'    # 狼人
    VILLAGER = 'villager'    # 村民
    SEER = 'seer'            # 预言家
    WITCH = 'witch'          # 女巫
    HUNTER = 'hunter'        # 猎人


class GameResult(str, Enum):
    """游戏结果"""
    ONGOING = 'ongoing'
    WEREWOLF_WIN = 'werewolf_win'
    VILLAGER_WIN = 'villager_win'


class KilledBy(str, Enum):
    """死亡原因"""
    VOTE = 'vote'              # 投票驱逐
    WEREWOLF = 'werewolf'      # 狼人杀死
    WITCH = 'witch'            # 女巫毒死

