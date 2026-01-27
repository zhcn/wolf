"""
游戏 API 路由
处理所有游戏相关的 HTTP 请求
"""
import logging

from flask import Blueprint, request, jsonify
from game_engine import get_or_create_game, get_game

bp = Blueprint('game', __name__, url_prefix='/api/rooms')

# 获取日志记录器
logger = logging.getLogger('api')

# ============== 辅助函数 ==============

def success_response(data, message="Success"):
    """成功响应"""
    return jsonify({
        'code': 200,
        'message': message,
        'data': data
    }), 200

def error_response(code, message, data=None):
    """错误响应"""
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    }), code if code < 500 else 500

# ============== API 接口 ==============

@bp.route('/<room_id>/assign-roles', methods=['POST'])
def assign_roles(room_id):
    """
    分配角色接口
    POST /rooms/{roomId}/assign-roles
    """
    logger.debug(f"🎮 [assign_roles] 房间: {room_id}")
    try:
        data = request.get_json()
        seat_count = data.get('seatCount', 12)
        logger.debug(f"📝 [assign_roles] 座位数: {seat_count}")

        # 获取或创建游戏
        game = get_or_create_game(room_id, seat_count)
        logger.debug(f"✅ [assign_roles] 游戏实例创建/获取成功")

        # 分配角色
        roles_by_seat = game.assign_roles()
        logger.info(f"🎭 [assign_roles] 角色分配完成: {roles_by_seat}")

        response = {
            'roomId': room_id,
            'rolesBySeat': roles_by_seat
        }
        logger.debug(f"📤 [assign_roles] 返回响应: {response}")
        return success_response(response, "Roles assigned successfully")

    except Exception as e:
        logger.error(f"❌ [assign_roles] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error assigning roles: {str(e)}")

@bp.route('/<room_id>/state', methods=['GET'])
def get_game_state(room_id):
    """
    获取游戏状态
    GET /rooms/{roomId}/state
    """
    logger.debug(f"📊 [get_state] 房间: {room_id}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [get_state] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        state = game.get_state()
        logger.debug(f"📤 [get_state] 游戏状态: {state}")
        return success_response(state, "Game state retrieved successfully")
    except Exception as e:
        logger.error(f"❌ [get_state] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error getting game state: {str(e)}")

@bp.route('/<room_id>/start-round', methods=['POST'])
def start_round(room_id):
    """
    开始新阶段
    POST /rooms/{roomId}/start-round
    """
    logger.debug(f"⏭️ [start_round] 房间: {room_id}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [start_round] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        phase, duration = game.start_round()
        logger.info(f"🔄 [start_round] 进入阶段 {phase}，持续 {duration}s")

        response = {
            'phase': phase,
            'durationSeconds': duration
        }
        logger.debug(f"📤 [start_round] 返回响应: {response}")
        return success_response(response, "Round started successfully")
    except Exception as e:
        logger.error(f"❌ [start_round] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error starting round: {str(e)}")

@bp.route('/<room_id>/speech', methods=['POST'])
def submit_speech(room_id):
    """
    提交发言
    POST /rooms/{roomId}/speech
    """
    data = request.get_json()
    seat = data.get('seat')
    text = data.get('text', '')
    logger.debug(f"💬 [speech] 房间: {room_id}, 发言者: {seat}号, 内容长度: {len(text)}")
    try:
        if not text or len(text) > 300:
            logger.warning(f"⚠️ [speech] 发言文本无效: 长度={len(text)}")
            return error_response(400, "Invalid speech text")

        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [speech] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        logger.info(f"✅ [speech] 发言记录: {seat}号说: {text}")
        response = {
            'success': True,
            'seat': seat
        }
        return success_response(response, "Speech submitted successfully")
    except Exception as e:
        logger.error(f"❌ [speech] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error submitting speech: {str(e)}")

@bp.route('/<room_id>/vote', methods=['POST'])
def submit_vote(room_id):
    """
    提交投票
    POST /rooms/{roomId}/vote
    """
    data = request.get_json()
    voter_seat = data.get('voterSeat')
    target_seat = data.get('targetSeat')
    logger.debug(f"🗳️ [vote] 房间: {room_id}, 投票者: {voter_seat}号, 目标: {target_seat}号")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [vote] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 提交投票
        success = game.submit_vote(voter_seat, target_seat)
        if not success:
            logger.warning(f"⚠️ [vote] 投票无效: {voter_seat}→{target_seat}")
            return error_response(400, "Invalid vote")

        logger.info(f"✅ [vote] 投票提交成功: {voter_seat}号投票给{target_seat}号")
        response = {
            'success': True,
            'voterSeat': voter_seat,
            'targetSeat': target_seat
        }
        return success_response(response, "Vote submitted successfully")
    except Exception as e:
        logger.error(f"❌ [vote] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error submitting vote: {str(e)}")

@bp.route('/<room_id>/night-action', methods=['POST'])
def submit_night_action(room_id):
    """
    提交晚上行动
    POST /rooms/{roomId}/night-action
    """
    data = request.get_json()
    player_seat = data.get('playerSeat')
    role = data.get('role')
    action_type = data.get('actionType')
    target_seat = data.get('targetSeat')
    logger.debug(f"🌙 [night_action] 房间: {room_id}, 玩家: {player_seat}号({role}), 行动: {action_type}, 目标: {target_seat}号")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [night_action] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 提交行动
        success = game.submit_night_action(player_seat, role, action_type, target_seat)
        if not success:
            logger.warning(f"⚠️ [night_action] 行动无效: {player_seat}号的{role}执行{action_type}")
            return error_response(400, "Invalid night action")

        logger.info(f"✅ [night_action] 行动成功: {player_seat}号({role})执行了{action_type}")
        response = {
            'success': True,
            'action': action_type,
            'result': f"Action completed successfully"
        }
        return success_response(response, "Night action submitted successfully")
    except Exception as e:
        logger.error(f"❌ [night_action] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error submitting night action: {str(e)}")

@bp.route('/<room_id>/messages', methods=['GET'])
def get_game_messages(room_id):
    """
    获取游戏消息（长轮询）
    GET /rooms/{roomId}/messages?after={lastMessageId}
    """
    last_message_id = request.args.get('after')
    logger.debug(f"📨 [messages] 房间: {room_id}, 最后消息ID: {last_message_id or '无'}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [messages] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 获取消息列表
        messages = []
        if last_message_id:
            # 获取某个消息之后的所有消息
            found = False
            for msg in game.game_state.messages:
                if found:
                    messages.append({
                        'id': msg.id,
                        'timestamp': msg.timestamp,
                        'type': msg.type,
                        'content': msg.content
                    })
                if msg.id == last_message_id:
                    found = True
        else:
            # 获取所有消息
            messages = [
                {
                    'id': msg.id,
                    'timestamp': msg.timestamp,
                    'type': msg.type,
                    'content': msg.content
                }
                for msg in game.game_state.messages
            ]

        logger.debug(f"📤 [messages] 返回 {len(messages)} 条消息")
        response = {
            'messages': messages
        }
        return success_response(response, "Messages retrieved successfully")
    except Exception as e:
        logger.error(f"❌ [messages] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error getting messages: {str(e)}")

@bp.route('/<room_id>/agent-speech', methods=['POST'])
def get_agent_speech(room_id):
    """
    获取 Agent 发言
    POST /rooms/{roomId}/agent-speech
    """
    data = request.get_json()
    seat = data.get('seat')
    logger.debug(f"🤖 [agent_speech] 房间: {room_id}, Agent座位: {seat}号")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [agent_speech] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # Agent 发言库
        speech_library = [
            '我觉得这一轮大家都表现得很不错。',
            '我注意到有些人的发言方式有点可疑。',
            '让我们冷静下来，好好分析一下情况。',
            '根据今天的讨论，我认为需要投票驱逐某个人。',
            '大家要相信彼此，团结起来对抗狼人。',
            '我的直觉告诉我这个人可能有问题。',
            '让我们投票吧，不要浪费时间。',
            '我赞同刚才的分析，非常有道理。',
            '我觉得需要更多的信息来做出判断。',
            '大家放心，我会尽力保护村民。',
            '这个发言听起来有点可疑，我需要考虑一下。',
            '我认为我们应该相信大多数人的投票结果。',
        ]

        import random
        speech_text = random.choice(speech_library)
        logger.info(f"🤖 [agent_speech] {seat}号Agent发言: {speech_text}")

        response = {
            'seat': seat,
            'text': speech_text
        }
        logger.debug(f"📤 [agent_speech] 返回响应: {response}")
        return success_response(response, "Agent speech generated successfully")
    except Exception as e:
        logger.error(f"❌ [agent_speech] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error generating agent speech: {str(e)}")

@bp.route('/<room_id>/advance-speaker', methods=['POST'])
def advance_speaker(room_id):
    """
    推进到下一个发言者
    POST /rooms/{roomId}/advance-speaker
    """
    logger.debug(f"🎤 [advance_speaker] 房间: {room_id}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [advance_speaker] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 推进发言者
        success = game.advance_speaker()
        if not success:
            logger.info(f"ℹ️ [advance_speaker] 所有人都发言完了，结束讨论阶段")
        else:
            logger.info(f"✅ [advance_speaker] 推进到下一个发言者")

        response = {
            'success': success,
            'currentSpeaker': game.game_state.speaking_order[game.game_state.current_speaker_index] if success and game.game_state.speaking_order else None
        }
        return success_response(response, "Speaker advanced successfully")
    except Exception as e:
        logger.error(f"❌ [advance_speaker] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error advancing speaker: {str(e)}")

@bp.route('/<room_id>/agent-action', methods=['POST'])
def get_agent_action(room_id):
    """
    获取 Agent 晚上行动
    POST /rooms/{roomId}/agent-action
    """
    data = request.get_json()
    seat = data.get('seat')
    role = data.get('role')
    available_targets = data.get('availableTargets', [])
    logger.debug(f"🌙 [agent_action] 房间: {room_id}, Agent座位: {seat}号, 角色: {role}, 可选目标: {available_targets}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [agent_action] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        if not available_targets:
            logger.warning(f"⚠️ [agent_action] 没有可用的目标")
            return error_response(400, "No available targets")

        import random

        # 根据角色生成不同的行动
        action_type = 'kill'  # 默认行动类型

        if role == 'werewolf':
            action_type = 'kill'
            target_seat = random.choice(available_targets)
            logger.info(f"🐺 [agent_action] {seat}号狼人选择杀死{target_seat}号")
        elif role == 'seer':
            action_type = 'check'
            target_seat = random.choice(available_targets)
            logger.info(f"🔮 [agent_action] {seat}号预言家选择检查{target_seat}号")
        elif role == 'witch':
            # 女巫随机选择救人或下毒
            action_type = random.choice(['save', 'save'])  # 倾向于救人
            target_seat = random.choice(available_targets)
            logger.info(f"🧙 [agent_action] {seat}号女巫选择{action_type}{target_seat}号")
        elif role == 'hunter':
            action_type = 'kill'
            target_seat = random.choice(available_targets) if available_targets else None
            logger.info(f"🏹 [agent_action] {seat}号猎人选择开枪{target_seat}号")
        else:
            target_seat = random.choice(available_targets) if available_targets else None

        response = {
            'seat': seat,
            'actionType': action_type,
            'targetSeat': target_seat
        }
        logger.debug(f"📤 [agent_action] 返回响应: {response}")
        return success_response(response, "Agent action generated successfully")
    except Exception as e:
        logger.error(f"❌ [agent_action] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error generating agent action: {str(e)}")

@bp.route('/<room_id>/health', methods=['GET'])
def health_check(room_id):
    """
    健康检查
    GET /rooms/{roomId}/health
    """
    try:
        game = get_game(room_id)
        return success_response({
            'status': 'ok',
            'roomId': room_id,
            'hasGame': game is not None
        }, "Health check passed")
    except Exception as e:
        return error_response(500, f"Health check failed: {str(e)}")

