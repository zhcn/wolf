"""
调试配置文件
用于在调试模式下指定玩家角色
"""

from typing import Optional

# 是否启用调试模式
DEBUG_MODE = True

# 玩家角色配置
# 格式: {"房间号_用户座位号": "角色名"}
# 示例: {"classic_1": "werewolf"} 表示在 classic 房间中，座位 1 的玩家固定为狼人
PLAYER_ROLE_CONFIG = {
    "classic_7": "werewolf",
    # "classic_2": "seer",
    # "classic_3": "witch",
}


def get_player_role(room_id: str, user_seat: int) -> Optional[str]:
    """
    获取指定玩家的角色配置

    Args:
        room_id: 房间号
        user_seat: 用户座位号

    Returns:
        角色名，如果没有配置则返回 None
    """
    if not DEBUG_MODE:
        return None

    key = f"{room_id}_{user_seat}"
    return PLAYER_ROLE_CONFIG.get(key)


def set_player_role(room_id: str, user_seat: int, role: str) -> None:
    """
    设置指定玩家的角色

    Args:
        room_id: 房间号
        user_seat: 用户座位号
        role: 角色名
    """
    key = f"{room_id}_{user_seat}"
    PLAYER_ROLE_CONFIG[key] = role
    print(f"[DEBUG] 设置房间 {room_id} 座位 {user_seat} 的角色为: {role}")

