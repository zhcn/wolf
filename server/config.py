"""
配置文件
从配置文件读取配置值
"""
import json
import os

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


def load_config() -> dict:
    """从配置文件加载配置"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"配置文件不存在: {CONFIG_FILE}\n"
            "请创建 config.json 文件并配置以下内容:\n"
            '{\n'
            '  "openai": {\n'
            '    "api_key": "你的API密钥",\n'
            '    "base_url": "https://aigc.sankuai.com/v1/openai/native",\n'
            '    "model": "gpt-4.1"\n'
            '  }\n'
            '}'
        )

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 验证必要的配置项
            if 'openai' not in config:
                raise ValueError("配置文件缺少 openai 配置段")
            if 'api_key' not in config.get('openai', {}) or not config.get('openai', {}).get('api_key'):
                raise ValueError("配置文件缺少 openai.api_key")
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"配置文件读取失败: {str(e)}")


def save_config(config: dict):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise RuntimeError(f"配置文件保存失败: {str(e)}")


# 加载配置
_config = load_config()

# 大模型 API 配置
OPENAI_API_KEY = _config.get('openai', {}).get('api_key', '')
OPENAI_BASE_URL = _config.get('openai', {}).get('base_url', '')
OPENAI_MODEL = _config.get('openai', {}).get('model', '')

# 验证配置完整性
if not OPENAI_API_KEY:
    raise ValueError("配置文件中缺少必需的 openai.api_key")
if not OPENAI_BASE_URL:
    raise ValueError("配置文件中缺少必需的 openai.base_url")

