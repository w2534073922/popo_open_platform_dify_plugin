import logging
import sys
from datetime import datetime, timedelta
from dify_plugin.config.logger_format import plugin_logger_handler
from models.popo_bot_callback_structures import PopoEventType, RobotEvent
from models.popo_bot_endpoint_settings_structures import PopoBotEndpointSettings

logger = logging.getLogger(__name__)
if sys.platform in ('win32', 'cygwin', 'darwin'):
    # 清空已有的handlers避免重复
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    # 为开发环境创建专门的handler
    dev_handler = logging.StreamHandler()
    dev_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    dev_handler.setFormatter(dev_formatter)
    logger.addHandler(dev_handler)
    logger.propagate = False  # 防止日志向父级传播
else:
    logger.setLevel(logging.INFO)
    logger.addHandler(plugin_logger_handler)

# 存储会话记忆
memory_dict = {}
# 记忆有效期，小时
memory_validity_period = 1

class PopoBotMemory:
    def __init__(self, bot_account: str, message_source: str, conversation_id: str, last_time: datetime):

        # 机器人账号
        self.bot_account = bot_account
        # 消息来源，群号或popo邮箱
        self.message_source = message_source
        # app的会话id
        self.conversation_id = conversation_id
        # 最后一次popo消息的时间
        self.last_time = last_time
        # self.last_app_id = last_app_id

    def to_dict(self) -> dict:
        return {
            "bot_account": self.bot_account,
            "message_source": self.message_source,
            "conversation_id": self.conversation_id,
            "last_time": self.last_time,
            # "last_app_id": self.last_app_id
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            bot_account=data["bot_account"],
            message_source=data["message_source"],
            conversation_id=data["conversation_id"],
            last_time=data["last_time"],
            # last_app_id=data["last_app_id"]
        )

# 设置会话记忆
def set_popobot_memory(rebot_event:RobotEvent, plugin_settings: PopoBotEndpointSettings, conversation_id: str) -> None:
    if rebot_event.event_type == PopoEventType.IM_P2P_TO_ROBOT_MSG:
        bot_account = rebot_event.event_data.from_
    else:
        bot_account = rebot_event.event_data.at_list[0]
    message_source = rebot_event.event_data.session_id
    key_name = get_memory_key_name(rebot_event,plugin_settings)
    memory_content = PopoBotMemory(bot_account, message_source, conversation_id, datetime.strptime(rebot_event.event_data.addtime, "%Y-%m-%d %H:%M:%S"))
    # session.storage.set(key_name, json.dumps(memory_content, ensure_ascii=False).encode('utf-8'))
    memory_dict[key_name] = memory_content
    logger.debug(f"存入记忆成功: keyName = {key_name}, memory_content = {memory_content.to_dict()}")

# 获取会话记忆
def get_popobot_memory(rebot_event:RobotEvent, plugin_settings: PopoBotEndpointSettings) -> "PopoBotMemory | None":
    key_name = get_memory_key_name(rebot_event,plugin_settings)
    # memory_content_dict = session.storage.get(key_name).decode('utf-8')
    memory_content = memory_dict.get(key_name)
    if memory_content is None:
        return None
    elif datetime.now() > memory_content.last_time + timedelta(hours=memory_validity_period):
        memory_dict.pop(key_name,None)
        return None
    else:
        return memory_content


def clear_memory(rebot_event:RobotEvent, plugin_settings: PopoBotEndpointSettings) -> None:
    key_name = get_memory_key_name(rebot_event,plugin_settings)
    memory_dict.pop(key_name,None)


def clear_all_memory() -> None:
    pass

def get_memory_key_name(rebot_event:RobotEvent, plugin_settings: PopoBotEndpointSettings) -> str:
    return "popobot_conversation_memory_" + plugin_settings.agent_app_id + "_" + plugin_settings.popo_app_key + "_" + rebot_event.event_data.session_id