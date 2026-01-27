"""
API 测试脚本
用于本地测试所有 API 接口
"""
import json

import requests

BASE_URL = "http://localhost:5000/api"
ROOM_ID = "test_room_001"

def print_response(title, response):
    """打印响应"""
    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"{'='*60}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"状态码: {response.status_code}")

def test_assign_roles():
    """测试分配角色"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/assign-roles",
        json={
            "seatCount": 12,
            "userSeat": 1
        }
    )
    print_response("1️⃣ 分配角色", response)
    return response.json()['data']['rolesBySeat']

def test_get_state():
    """测试获取游戏状态"""
    response = requests.get(f"{BASE_URL}/rooms/{ROOM_ID}/state")
    print_response("2️⃣ 获取游戏状态", response)
    return response.json()['data']

def test_start_round():
    """测试开始新阶段"""
    response = requests.post(f"{BASE_URL}/rooms/{ROOM_ID}/start-round")
    print_response("3️⃣ 开始新阶段", response)
    return response.json()['data']

def test_submit_speech():
    """测试提交发言"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/speech",
        json={
            "seat": 1,
            "text": "我认为2号和3号看起来很可疑，像是狼人..."
        }
    )
    print_response("4️⃣ 提交发言", response)

def test_submit_vote():
    """测试提交投票"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/vote",
        json={
            "voterSeat": 1,
            "targetSeat": 3
        }
    )
    print_response("5️⃣ 提交投票", response)

def test_submit_night_action_werewolf():
    """测试狼人杀人"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/night-action",
        json={
            "playerSeat": 1,
            "role": "werewolf",
            "actionType": "kill",
            "targetSeat": 5
        }
    )
    print_response("6️⃣ 狼人杀人", response)

def test_submit_night_action_seer():
    """测试预言家检查"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/night-action",
        json={
            "playerSeat": 2,
            "role": "seer",
            "actionType": "check",
            "targetSeat": 3
        }
    )
    print_response("7️⃣ 预言家检查", response)

def test_submit_night_action_witch():
    """测试女巫救人"""
    response = requests.post(
        f"{BASE_URL}/rooms/{ROOM_ID}/night-action",
        json={
            "playerSeat": 3,
            "role": "witch",
            "actionType": "save",
            "targetSeat": 5
        }
    )
    print_response("8️⃣ 女巫救人", response)

def test_get_messages():
    """测试获取游戏消息"""
    response = requests.get(f"{BASE_URL}/rooms/{ROOM_ID}/messages")
    print_response("9️⃣ 获取游戏消息", response)

def test_health_check():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/rooms/{ROOM_ID}/health")
    print_response("🏥 健康检查", response)

def run_all_tests():
    """运行所有测试"""
    print("\n" + "🎮" * 30)
    print("🎮 狼人杀游戏后端 API 测试")
    print("🎮" * 30)

    try:
        # 1. 分配角色
        roles = test_assign_roles()

        # 2. 获取游戏状态
        state = test_get_state()

        # 3. 开始第一个阶段
        round_info = test_start_round()
        print(f"\n⏱️  当前阶段将持续 {round_info['durationSeconds']} 秒")

        # 4. 提交发言
        test_submit_speech()

        # 5. 提交投票
        test_submit_vote()

        # 6. 狼人杀人
        test_submit_night_action_werewolf()

        # 7. 预言家检查
        test_submit_night_action_seer()

        # 8. 女巫救人
        test_submit_night_action_witch()

        # 9. 获取消息
        test_get_messages()

        # 10. 健康检查
        test_health_check()

        print("\n" + "✅" * 30)
        print("✅ 所有测试完成！")
        print("✅" * 30 + "\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到后端服务")
        print("请确保后端服务正在运行: python app.py")
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")

if __name__ == '__main__':
    run_all_tests()

