"""
游戏 API 路由（重构版）
使用状态机架构处理所有游戏相关的 HTTP 请求
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

    请求体:
        {
            "seatCount": 12,
            "mode": "classic"  // 可选，默认为 classic
        }
    """
    logger.debug(f"🎮 [assign_roles] 房间: {room_id}")
    try:
        data = request.get_json()
        seat_count = data.get('seatCount', 12)
        mode = data.get('mode', 'classic')
        logger.debug(f"📝 [assign_roles] 座位数: {seat_count}, 模式: {mode}")

        # 获取或创建游戏
        game = get_or_create_game(room_id, mode, seat_count)
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
    推进到下一阶段
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

    请求体:
        {
            "seat": 1,
            "text": "我的发言内容"
        }
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

        success = game.submit_speech(seat, text)
        if not success:
            logger.warning(f"⚠️ [speech] 发言提交失败")
            return error_response(400, "Failed to submit speech")

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

    请求体:
        {
            "voterSeat": 1,
            "targetSeat": 2
        }
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

    请求体:
        {
            "playerSeat": 1,
            "role": "werewolf",
            "actionType": "kill",
            "targetSeat": 2
        }
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
        all_messages = game.get_messages()
        messages = []

        if last_message_id:
            # 获取某个消息之后的所有消息
            found = False
            for msg in all_messages:
                if found:
                    messages.append(msg)
                if msg['id'] == last_message_id:
                    found = True
        else:
            # 获取所有消息
            messages = all_messages

        logger.debug(f"📤 [messages] 返回 {len(messages)} 条消息")
        response = {
            'messages': messages
        }
        return success_response(response, "Messages retrieved successfully")
    except Exception as e:
        logger.error(f"❌ [messages] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error getting messages: {str(e)}")


@bp.route('/<room_id>/complete-announcement', methods=['POST'])
def complete_announcement(room_id):
    """
    清除播报信息（前端播报完成后调用）
    POST /rooms/{roomId}/complete-announcement
    """
    logger.debug(f"✅ [complete_announcement] 房间: {room_id}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [complete_announcement] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 清除播报信息（播报是附加信息，不影响游戏状态）
        game.state_machine.context.extensions.pop('announcement', None)
        game.state_machine.context.extensions.pop('announcement_time', None)

        logger.info(f"✅ [complete_announcement] 播报信息已清除")
        response = {
            'success': True
        }
        return success_response(response, "Announcement completed successfully")
    except Exception as e:
        logger.error(f"❌ [complete_announcement] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error completing announcement: {str(e)}")


@bp.route('/<room_id>/agent-speech', methods=['POST'])
def get_agent_speech(room_id):
    """
    获取 Agent 发言
    POST /rooms/{roomId}/agent-speech

    请求体:
        {
            "seat": 1
        }
    """
    data = request.get_json()
    seat = data.get('seat')
    logger.debug(f"🤖 [agent_speech] 房间: {room_id}, Agent座位: {seat}号")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [agent_speech] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        # 使用大模型生成发言
        from agent_decision import generate_agent_speech
        speech_text = generate_agent_speech(game.state_machine.context, seat)

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

        # 获取当前发言者
        state = game.get_state()
        current_speaker = state.get('currentSpeaker')

        response = {
            'success': success,
            'currentSpeaker': current_speaker
        }
        return success_response(response, "Speaker advanced successfully")
    except Exception as e:
        logger.error(f"❌ [advance_speaker] 错误: {str(e)}", exc_info=True)
        return error_response(500, f"Error advancing speaker: {str(e)}")


@bp.route('/<room_id>/agent-vote', methods=['POST'])
def agent_vote(room_id):
    """
    Agent 投票
    POST /rooms/{roomId}/agent-vote

    请求体:
    {
      "seat": 1
    }
    """
    logger.debug(f"🗳️ [agent_vote] 房间: {room_id}")
    try:
        game = get_game(room_id)
        if not game:
            logger.warning(f"⚠️ [agent_vote] 房间不存在: {room_id}")
            return error_response(404, f"Game room {room_id} not found")

        data = request.get_json()
        seat = data.get('seat')

        if not seat:
            logger.warning(f"⚠️ [agent_vote] 缺少座位号")
            return error_response(400, "Missing seat number")

        # Agent 投票
        success, message, result = game.agent_vote(seat)

        if not success:
            logger.warning(f"⚠️ [agent_vote] 投票失败: {message}")
            return error_response(400, message)

        logger.info(f"✅ [agent_vote] Agent {seat}号 投票给 {result.get('targetSeat')}")

        return success_response(result, "Agent voted successfully")

    except Exception as e:
        logger.error(f"❌ [agent_vote] 错误: {str(e)}", exc_info=True)
        return error_response(500, str(e))


@bp.route('/<room_id>/agent-action', methods=['POST'])
def get_agent_action(room_id):
    """
    获取 Agent 晚上行动
    POST /rooms/{roomId}/agent-action

    请求体:
        {
            "seat": 1,
            "role": "werewolf",
            "availableTargets": [2, 3, 4]
        }
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

        # 使用智能决策系统
        from agent_decision import decide_agent_action

        # 获取游戏状态上下文
        state_machine = game.state_machine
        context = state_machine.context

        # 让 Agent 做出决策
        decision = decide_agent_action(room_id, seat, role, available_targets, context)

        response = {
            'seat': decision['seat'],
            'actionType': decision['actionType'],
            'targetSeat': decision['targetSeat']
        }
        logger.debug(f"📤 [agent_action] 返回响应: {response}, 原因: {decision.get('reason', '')}")
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

