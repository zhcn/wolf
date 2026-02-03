"""
Agent 决策系统

为不同角色的 AI Agent 提供智能决策，根据游戏上下文做出合理行动。
每个角色只能根据自己的视角信息进行决策。
"""
import logging
import random
from typing import List, Dict, Optional

import openai

# 导入配置
from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from state_machines import Role
from state_machines.state_context import GameStateContext

logger = logging.getLogger('agent_decision')

# 初始化 OpenAI 客户端
try:
    llm_client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )
    logger.info(f"已初始化大模型客户端: {OPENAI_MODEL}")
except Exception as e:
    logger.error(f"大模型客户端初始化失败: {str(e)}")
    llm_client = None


def generate_agent_speech(context: GameStateContext, seat: int) -> str:
    """
    为 Agent 生成白天讨论发言

    Args:
        context: 游戏状态上下文
        seat: Agent 座位

    Returns:
        发言文本
    """
    agent = context.players.get(seat)
    if not agent:
        return '我没什么好说的。'

    role_name = agent.role.value if agent.role else 'unknown'

    # 获取历史对话消息
    messages_history = context.messages

    # 构建历史对话文本
    history_text = ""
    if messages_history:
        history_text = "\n".join(
            f"[Round {msg.content.get('round', '?')}] {msg.content.get('message', '')}" for msg in messages_history[-10:]  # 只取最近10条
        )

    # 获取存活玩家信息
    alive_players = context.get_alive_players()

    # === 角色信息（不同角色能看到不同的内容）===
    role_info = ""
    if agent.role == Role.WEREWOLF:
        # 狼人视角：看到所有狼人队友的身份
        if context.werewolf_context:
            teammates = context.werewolf_context.get('teammates', [])
            werewolf_info = [f"{s}号是狼人" for s in teammates]
            role_info = "狼人视角：\n" + "\n".join(werewolf_info)
        else:
            role_info = "狼人视角：\n无队友信息"
    elif agent.role == Role.SEER or agent.role == Role.WITCH or agent.role == Role.HUNTER or agent.role == Role.VILLAGER:
        # 预言家、女巫、猎人、村民：只能看到自己的角色
        role_info = f"神职/村民视角：\n{seat}号是{role_name}"

    # === 动作信息（不同角色特有的夜晚行动信息）===
    action_info = ""
    if agent.role == Role.WEREWOLF:
        # 狼人：知道昨晚杀的人
        if context.last_dead_player and context.last_dead_player.get('killed_by') == 'werewolf':
            action_info = f"\n夜晚行动信息：\n昨晚击杀了{context.last_dead_player.get('seat', '未知')}号"
    elif agent.role == Role.SEER:
        # 预言家：查看历史
        if context.seer_context:
            action_info = "\n夜晚行动信息：\n" + "\n".join(
                f"第{c.get('round', '?')}晚查了{c.get('seat', '?')}号，结果是{c.get('result', '?')}"
                for c in context.seer_context
            )
    elif agent.role == Role.WITCH:
        # 女巫：药水状态和使用历史
        if context.witch_context:
            action_info = f"\n夜晚行动信息：\n解药状态：{'有' if context.witch_context.get('has_save_potion') else '已使用'}\n毒药状态：{'有' if context.witch_context.get('has_poison_potion') else '已使用'}"
            saved = context.witch_context.get('saved_history', [])
            if saved:
                action_info += f"\n救过的玩家：{', '.join(map(str, saved))}"
    # 猎人和村民：没有特殊夜晚行动信息

    prompt = f"""你是一个狼人杀游戏的玩家。

【游戏规则】
- 狼人阵营：狼人每晚选择一名玩家击杀
- 神职阵营：
  * 预言家：每晚查验一名玩家的身份
  * 女巫：有一瓶解药（救被狼人杀的人）和一瓶毒药（毒死一人），同一晚只能使用一瓶
  * 猎人：死亡时可开枪带走一人
- 平民阵营：村民，晚上不行动
- 投票规则：白天所有人投票，票数最多者出局

【角色信息】
座位号：{seat}
{role_info}

【游戏状态】
当前轮次：第 {context.round} 轮
存活玩家：{', '.join(map(str, alive_players))}
今晚被狼人击杀：{context.werewolf_killed if context.werewolf_killed else '无'}号
昨晚死亡：{context.last_dead_player.get('seat', '无') if context.last_dead_player else '无'}号（{context.last_dead_player.get('killed_by', 'N/A') if context.last_dead_player else 'N/A'}）
{action_info}

【历史对话】（最近10条）
{history_text if history_text else '暂无对话'}

【任务】
现在进入白天讨论阶段，轮到你发言了。
请根据你的角色和游戏状态，生成一段自然的发言内容（50-200字）。
发言要符合你的角色身份和游戏情境。

返回纯文本发言内容，不要有多余格式："""

    response = llm_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "你是狼人杀游戏的 AI 玩家，需要根据角色和游戏状态生成自然的发言。"},
            {"role": "user", "content": prompt}
        ],
        stream=False,
        max_tokens=500,
        temperature=0.8
    )

    speech = response.choices[0].message.content.strip()

    logger.debug(f"Agent {seat} ({role_name}) 发言: {speech}")
    return speech


class AgentDecision:
    """Agent 决策基类"""

    def __init__(self, context: GameStateContext, agent_seat: int):
        self.context = context
        self.agent_seat = agent_seat
        self.agent = context.players.get(agent_seat)

    def get_alive_players_except_self(self) -> List[int]:
        """获取除自己以外的存活玩家"""
        alive = self.context.get_alive_players()
        return [seat for seat in alive if seat != self.agent_seat]

    def get_known_teammates(self) -> List[int]:
        """获取已知队友（子类实现）"""
        return []

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """决定晚上行动（子类必须实现）"""
        raise NotImplementedError

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """决定投票（子类可以重写）"""
        return {
            'voterSeat': self.agent_seat,
            'targetSeat': random.choice(available_targets) if available_targets else None,
            'reason': '随机投票'
        }

    def call_llm_decision(self, decision_type: str, context_info: str, available_targets: List[int]) -> Optional[Dict]:
        """
        调用大模型进行决策

        Args:
            decision_type: 决策类型 ('night_action' 或 'vote')
            context_info: 上下文信息
            available_targets: 可选目标列表

        Returns:
            决策结果
        """
        role_name = self.agent.role.value if self.agent.role else 'unknown'
        targets_str = ', '.join(map(str, available_targets))

        # 获取历史对话消息
        messages_history = self.context.messages

        # 构建历史对话文本
        history_text = ""
        if messages_history:
            history_text = "\n历史对话：\n" + "\n".join(
                f"[Round {msg.content.get('round', '?')}] {msg.content.get('message', '')}" for msg in messages_history
            )

        prompt = f"""你是一个狼人杀游戏的玩家。

【游戏规则】
- 狼人阵营：狼人每晚选择一名玩家击杀
- 神职阵营：
  * 预言家：每晚查验一名玩家的身份
  * 女巫：有一瓶解药（救被狼人杀的人）和一瓶毒药（毒死一人），同一晚只能使用一瓶
  * 猎人：死亡时可开枪带走一人
- 平民阵营：村民，晚上不行动
- 投票规则：白天所有人投票，票数最多者出局

【你的信息】
- 角色：{role_name}
- 座位号：{self.agent_seat}

【游戏上下文】
{context_info}
{history_text}

【当前任务】
决策类型：{decision_type}
可选目标：{targets_str}

请根据你作为 {role_name} 的角色视角和游戏规则，做出合理的决策。
直接返回 JSON 格式结果：
{{
    "targetSeat": 目标座位号数字,
    "reason": "决策原因简短描述"
}}"""

        response = llm_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是狼人杀游戏的 AI 玩家，需要根据角色和游戏状态做出合理决策。只返回 JSON 格式结果。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=1000,
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        # 尝试解析 JSON
        import json
        # 移除可能的 markdown 代码块标记
        content = content.replace('```json', '').replace('```', '').strip()
        result = json.loads(content)

        target = result.get('targetSeat')
        if target is not None and target not in available_targets and available_targets:
            # 如果目标无效，随机选择
            target = random.choice(available_targets)
            result['reason'] = f"{result.get('reason', '')}（目标无效，随机选择）"

        logger.debug(f"大模型决策: {decision_type}, 目标: {target}, 原因: {result.get('reason', '')}")
        return result


class WerewolfAgent(AgentDecision):
    """狼人 Agent 决策"""

    def get_known_teammates(self) -> List[int]:
        """获取所有狼人队友"""
        try:
            teammates = []
            for seat, player in self.context.players.items():
                if seat != self.agent_seat and player.alive and player.role == Role.WEREWOLF:
                    teammates.append(seat)
            return teammates
        except Exception as e:
            logger.error(f"[WerewolfAgent] get_known_teammates 失败: {str(e)}")
            return []

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """狼人晚上决策"""
        try:
            teammates = self.get_known_teammates()
            context_info = f"""当前轮次：第 {self.context.round} 轮
狼人队友：{', '.join(map(str, teammates))}
存活玩家：{', '.join(map(str, self.context.get_alive_players()))}"""

            llm_result = self.call_llm_decision('night_action', context_info, available_targets)
            if llm_result:
                target = llm_result.get('targetSeat')
                # 确保不杀队友
                if target not in teammates:
                    return {
                        'seat': self.agent_seat,
                        'actionType': 'kill',
                        'targetSeat': target,
                        'reason': llm_result.get('reason', '')
                    }

            # 大模型不可用或决策无效，使用规则决策
            targets = [t for t in available_targets if t not in teammates]
            if not targets:
                targets = available_targets

            target = random.choice(targets) if targets else None
            logger.info(f"[WerewolfAgent] 随机击杀: {target}")
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': target,
                'reason': '随机击杀'
            }
        except Exception as e:
            logger.error(f"[WerewolfAgent] decide_night_action 失败: {str(e)}")
            # 返回随机击杀作为后备
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': None,
                'reason': '异常后备决策'
            }

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """狼人投票决策"""
        try:
            teammates = self.get_known_teammates()
            votes_info = ', '.join(
                f'{s}号投给{p.voted_for}' for s, p in self.context.players.items()
                if p.alive and p.voted_for
            )
            context_info = f"""当前轮次：第 {self.context.round} 轮
狼人队友：{', '.join(map(str, teammates))}
存活玩家：{', '.join(map(str, self.context.get_alive_players()))}
已投票情况：{votes_info if votes_info else '暂无'}"""

            llm_result = self.call_llm_decision('vote', context_info, available_targets)
            if llm_result:
                target = llm_result.get('targetSeat')
                # 确保不投队友
                if target not in teammates:
                    return {
                        'voterSeat': self.agent_seat,
                        'targetSeat': target,
                        'reason': llm_result.get('reason', '')
                    }

            # 大模型不可用或决策无效，使用规则决策
            targets = [t for t in available_targets if t not in teammates]
            if not targets:
                targets = available_targets

            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '随机投票'
            }
        except Exception as e:
            logger.error(f"[WerewolfAgent] decide_vote 失败: {str(e)}", exc_info=True)
            # 返回随机投票作为后备
            targets = [t for t in available_targets if t != self.agent_seat]
            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '异常后备决策'
            }


class SeerAgent(AgentDecision):
    """预言家 Agent 决策"""

    def __init__(self, context: GameStateContext, agent_seat: int):
        super().__init__(context, agent_seat)
        self.checked_history: List[Dict] = []  # 记录查验历史

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """预言家晚上决策"""
        try:
            checked_seats = [check.get('seat') for check in self.checked_history if check.get('seat') is not None]
            context_info = f"""当前轮次：第 {self.context.round} 轮
已查验过的玩家：{', '.join(map(str, checked_seats)) if checked_seats else '无'}
存活玩家：{', '.join(map(str, self.context.get_alive_players()))}"""

            llm_result = self.call_llm_decision('night_action', context_info, available_targets)
            if llm_result:
                target = llm_result.get('targetSeat')
                # 确保不重复查验
                if target not in checked_seats:
                    self.checked_history.append({
                        'seat': target,
                        'round': self.context.round,
                    })
                    return {
                        'seat': self.agent_seat,
                        'actionType': 'check',
                        'targetSeat': target,
                        'reason': llm_result.get('reason', '')
                    }

            # 大模型不可用或决策无效，使用规则决策
            targets = [t for t in available_targets if t not in checked_seats]
            if not targets:
                targets = available_targets

            target = random.choice(targets) if targets else None

            # 记录查验
            self.checked_history.append({
                'seat': target,
                'round': self.context.round,
            })
            logger.info(f"[SeerAgent] 查验 {target}")
            return {
                'seat': self.agent_seat,
                'actionType': 'check',
                'targetSeat': target,
                'reason': '查验未知身份'
            }
        except Exception as e:
            logger.error(f"[SeerAgent] decide_night_action 失败: {str(e)}", exc_info=True)
            # 返回随机查验作为后备
            return {
                'seat': self.agent_seat,
                'actionType': 'check',
                'targetSeat': None,
                'reason': '异常后备决策'
            }

    def get_checked_history(self) -> List[Dict]:
        """获取查验历史（用于后续发言）"""
        return self.checked_history

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """预言家投票决策"""
        try:
            # 查找已知的狼人（如果查到了）
            for check in self.checked_history:
                seat = check.get('seat')
                if seat is None:
                    continue
                checked_player = self.context.players.get(seat)
                if checked_player and checked_player.role == Role.WEREWOLF:
                    return {
                        'voterSeat': self.agent_seat,
                        'targetSeat': seat,
                        'reason': '投已知狼人'
                    }

            # 没有已知狼人，随机投票
            target = random.choice(available_targets) if available_targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '随机投票'
            }
        except Exception as e:
            logger.error(f"[SeerAgent] decide_vote 失败: {str(e)}", exc_info=True)
            # 返回随机投票作为后备
            targets = [t for t in available_targets if t != self.agent_seat]
            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '异常后备决策'
            }


class WitchAgent(AgentDecision):
    """女巫 Agent 决策"""

    def __init__(self, context: GameStateContext, agent_seat: int):
        super().__init__(context, agent_seat)
        self.has_save_potion = True  # 是否有解药
        self.has_poison_potion = True  # 是否有毒药
        self.saved_history: List[int] = []  # 记录救过的玩家

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """女巫晚上决策"""
        try:
            werewolf_killed = self.context.werewolf_killed

            # 先尝试使用大模型决策
            context_info = f"""当前轮次：第 {self.context.round} 轮
今晚被狼人击杀：{werewolf_killed}号{f'（已死亡）' if werewolf_killed else '无'}
存活玩家：{', '.join(map(str, self.context.get_alive_players()))}
解药状态：{'有' if self.has_save_potion else '已使用'}
毒药状态：{'有' if self.has_poison_potion else '已使用'}
救过的玩家：{', '.join(map(str, self.saved_history)) if self.saved_history else '无'}"""

            llm_result = self.call_llm_decision('night_action', context_info, available_targets)
            if llm_result:
                target = llm_result.get('targetSeat')

                # 大模型决策处理
                if target is None or target == werewolf_killed:
                    # 救人或不使用
                    if werewolf_killed and self.has_save_potion and target == werewolf_killed:
                        self.has_save_potion = False
                        self.saved_history.append(werewolf_killed)
                        return {
                            'seat': self.agent_seat,
                            'actionType': 'save',
                            'targetSeat': werewolf_killed,
                            'reason': llm_result.get('reason', '')
                        }
                    else:
                        return {
                            'seat': self.agent_seat,
                            'actionType': 'save',
                            'targetSeat': None,
                            'reason': llm_result.get('reason', '')
                        }
                elif self.has_poison_potion and target in available_targets:
                    # 毒人
                    self.has_poison_potion = False
                    return {
                        'seat': self.agent_seat,
                        'actionType': 'poison',
                        'targetSeat': target,
                        'reason': llm_result.get('reason', '')
                    }

            # 大模型不可用或决策无效，使用规则决策
            # 如果有人被杀，且还有解药
            if werewolf_killed and self.has_save_potion:
                self.has_save_potion = False
                self.saved_history.append(werewolf_killed)
                return {
                    'seat': self.agent_seat,
                    'actionType': 'save',
                    'targetSeat': werewolf_killed,
                    'reason': '解药救人'
                }

            # 不使用任何药
            return {
                'seat': self.agent_seat,
                'actionType': 'save',
                'targetSeat': None,
                'reason': '不使用药水'
            }
        except Exception as e:
            logger.error(f"[WitchAgent] decide_night_action 失败: {str(e)}", exc_info=True)
            # 返回默认决策：不使用药水
            return {
                'seat': self.agent_seat,
                'actionType': 'save',
                'targetSeat': None,
                'reason': '异常后备决策'
            }

    def get_potion_status(self) -> Dict:
        """获取药水状态"""
        return {
            'hasSavePotion': self.has_save_potion,
            'hasPoisonPotion': self.has_poison_potion,
            'savedHistory': self.saved_history
        }

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """女巫投票决策"""
        try:
            context_info = f"""当前轮次：第 {self.context.round} 轮
存活玩家：{', '.join(map(str, self.context.get_alive_players()))}
救过的玩家：{', '.join(map(str, self.saved_history)) if self.saved_history else '无'}"""

            llm_result = self.call_llm_decision('vote', context_info, available_targets)
            if llm_result:
                return {
                    'voterSeat': self.agent_seat,
                    'targetSeat': llm_result.get('targetSeat'),
                    'reason': llm_result.get('reason', '')
                }

            # 大模型不可用，随机投票
            target = random.choice(available_targets) if available_targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '随机投票'
            }
        except Exception as e:
            logger.error(f"[WitchAgent] decide_vote 失败: {str(e)}", exc_info=True)
            # 返回随机投票作为后备
            targets = [t for t in available_targets if t != self.agent_seat]
            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '异常后备决策'
            }


class HunterAgent(AgentDecision):
    """猎人 Agent 决策（晚上不行动，死后开枪）"""

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """猎人不参与晚上行动"""
        try:
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': None,
                'reason': '猎人不晚上行动'
            }
        except Exception as e:
            logger.error(f"[HunterAgent] decide_night_action 失败: {str(e)}", exc_info=True)
            # 返回默认决策
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': None,
                'reason': '异常后备决策'
            }

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """猎人投票决策（随机）"""
        try:
            target = random.choice(available_targets) if available_targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '随机投票'
            }
        except Exception as e:
            logger.error(f"[HunterAgent] decide_vote 失败: {str(e)}", exc_info=True)
            # 返回随机投票作为后备
            targets = [t for t in available_targets if t != self.agent_seat]
            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '异常后备决策'
            }


class VillagerAgent(AgentDecision):
    """村民 Agent 决策"""

    def decide_night_action(self, available_targets: List[int]) -> Dict:
        """村民不参与晚上行动"""
        try:
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': None,
                'reason': '村民不晚上行动'
            }
        except Exception as e:
            logger.error(f"[VillagerAgent] decide_night_action 失败: {str(e)}", exc_info=True)
            # 返回默认决策
            return {
                'seat': self.agent_seat,
                'actionType': 'kill',
                'targetSeat': None,
                'reason': '异常后备决策'
            }

    def decide_vote(self, available_targets: List[int]) -> Dict:
        """村民投票决策（随机）"""
        try:
            target = random.choice(available_targets) if available_targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '随机投票'
            }
        except Exception as e:
            logger.error(f"[VillagerAgent] decide_vote 失败: {str(e)}", exc_info=True)
            # 返回随机投票作为后备
            targets = [t for t in available_targets if t != self.agent_seat]
            target = random.choice(targets) if targets else None
            return {
                'voterSeat': self.agent_seat,
                'targetSeat': target,
                'reason': '异常后备决策'
            }


# Agent 实例缓存（保存每个 Agent 的决策上下文）
agent_contexts: Dict[str, Dict[int, AgentDecision]] = {}


def get_agent_context(room_id: str, seat: int, context: GameStateContext) -> AgentDecision:
    """
    获取 Agent 决策上下文

    Args:
        room_id: 房间 ID
        seat: Agent 座位
        context: 游戏状态上下文

    Returns:
        AgentDecision 实例
    """
    if room_id not in agent_contexts:
        agent_contexts[room_id] = {}

    # 如果已存在该 Agent 的上下文，返回
    if seat in agent_contexts[room_id]:
        return agent_contexts[room_id][seat]

    # 创建新的 Agent 上下文
    agent = context.players.get(seat)
    if not agent or not agent.role:
        raise ValueError(f"Agent {seat} not found or no role assigned")

    if agent.role == Role.WEREWOLF:
        agent_contexts[room_id][seat] = WerewolfAgent(context, seat)
    elif agent.role == Role.SEER:
        agent_contexts[room_id][seat] = SeerAgent(context, seat)
    elif agent.role == Role.WITCH:
        agent_contexts[room_id][seat] = WitchAgent(context, seat)
    elif agent.role == Role.HUNTER:
        agent_contexts[room_id][seat] = HunterAgent(context, seat)
    elif agent.role == Role.VILLAGER:
        agent_contexts[room_id][seat] = VillagerAgent(context, seat)
    else:
        # 未知角色使用村民逻辑
        agent_contexts[room_id][seat] = VillagerAgent(context, seat)

    return agent_contexts[room_id][seat]


def clear_agent_contexts(room_id: str):
    """清除指定房间的 Agent 上下文（用于游戏重置）"""
    if room_id in agent_contexts:
        del agent_contexts[room_id]


def decide_agent_action(room_id: str, seat: int, role: str, available_targets: List[int], context: GameStateContext) -> Dict:
    """
    为 Agent 决策晚上行动

    Args:
        room_id: 房间 ID
        seat: Agent 座位
        role: 角色
        available_targets: 可选目标列表
        context: 游戏状态上下文

    Returns:
        决策结果 {'seat', 'actionType', 'targetSeat', 'reason'}
    """
    try:
        agent = get_agent_context(room_id, seat, context)
        decision = agent.decide_night_action(available_targets)

        # 记录决策日志
        logger.debug(f"Agent {seat} ({role}) 决策: {decision.get('actionType', 'unknown')} -> {decision.get('targetSeat', 'None')}, 原因: {decision.get('reason', 'N/A')}")

        return {
            'seat': seat,
            'actionType': decision.get('actionType', 'kill'),
            'targetSeat': decision.get('targetSeat'),
            'reason': decision.get('reason', '')
        }
    except Exception as e:
        logger.error(f"Agent {seat} 决策失败: {str(e)}", exc_info=True)
        # 重新抛出异常，让上层处理
        raise


def decide_agent_vote(room_id: str, seat: int, available_targets: List[int], context: GameStateContext) -> Dict:
    """
    为 Agent 决策投票

    Args:
        room_id: 房间 ID
        seat: Agent 座位
        available_targets: 可选目标列表
        context: 游戏状态上下文

    Returns:
        决策结果 {'voterSeat', 'targetSeat', 'reason'}
    """
    try:
        agent = get_agent_context(room_id, seat, context)
        decision = agent.decide_vote(available_targets)

        # 记录决策日志
        logger.debug(f"Agent {seat} 投票给 {decision.get('targetSeat', 'None')}, 原因: {decision.get('reason', 'N/A')}")

        return {
            'voterSeat': decision.get('voterSeat', seat),
            'targetSeat': decision.get('targetSeat'),
            'reason': decision.get('reason', '')
        }
    except Exception as e:
        logger.error(f"Agent {seat} 投票决策失败: {str(e)}", exc_info=True)
        # 重新抛出异常，让上层处理
        raise

