"""
测试导入
验证所有模块可以正确导入
"""
import os
import sys

# 添加 server 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("测试导入...")
print("=" * 50)

try:
    from state_machines import (
        GameMode,
        Role,
        GameResult,
        KilledBy,
        GameStateContext,
        Player,
        GameMessage,
        BaseStateMachine,
        ClassicWerewolfStateMachine,
        create_state_machine,
        register_state_machine,
        get_supported_modes,
    )
    print("✅ state_machines 模块导入成功")
except Exception as e:
    print(f"❌ state_machines 模块导入失败: {e}")

try:
    from game_engine import GameEngine, get_or_create_game, get_game
    print("✅ game_engine 模块导入成功")
except Exception as e:
    print(f"❌ game_engine 模块导入失败: {e}")

try:
    from routes import game_routes
    print("✅ routes.game_routes 模块导入成功")
except Exception as e:
    print(f"❌ routes.game_routes 模块导入失败: {e}")

print("=" * 50)
print("所有导入测试完成！")

