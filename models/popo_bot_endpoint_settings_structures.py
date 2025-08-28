from collections.abc import Mapping
from enum import Enum
import json
from typing import Optional, Any


class AgentType(Enum):
    CHAT = "chat"
    CHATFLOW = "chatflow"
    WORKFLOW = "workflow"


class PopoBotEndpointSettings:
    def __init__(self, settings: Mapping):
        # 机器人token
        self.token: Optional[str] = settings.get("token")
        # 消息加密密钥
        self.aes_key: Optional[str] = settings.get("aesKey")
        # 处理消息的智能体
        agent_settings: Optional[Mapping[Any]] = settings.get("agent")
        self.agent_app_id: Optional[str] = agent_settings.get("app_id") if agent_settings else None
        self.agent_files: Optional[Any] = agent_settings.get("files") if agent_settings else None
        self.agent_inputs: Optional[Any] = agent_settings.get("inputs") if agent_settings else None
        self.selector_type: Optional[str] = agent_settings.get("type") if agent_settings else None
        # 应用类型（必须与绑定的智能体一致）
        agent_type_value: Optional[str] = settings.get("agent_type")
        self.agent_type: str = AgentType(agent_type_value).value if agent_type_value else ""
        # 机器人自动回复智能体执行结果
        self.is_auto_reply: bool = settings.get("is_auto_reply", False)
        # popo机器人的appKey
        self.popo_app_key: Optional[str] = settings.get("popo_app_key")
        # popo机器人的appSecret
        self.popo_app_secret: Optional[str] = settings.get("popo_app_secret")
        # 自动回复时的预设消息（不填则无）
        self.auto_reply_preset_message: Optional[str] = settings.get("auto_reply_preset_message")
        # 工作流类型应用的输入字段
        self.workflow_input_field: str = settings.get("workflow_input_field", "popo_input_message")
        # 工作流类型应用的输出字段
        self.workflow_output_field: str = settings.get("workflow_output_field", "popo_output_message")
        # 日志上报地址（可忽略，线上插件的运行日志将post到该地址）
        # self.log_reporting_address = settings.get("logReportingAddress") or "https://log-jystudy.app.codewave.163.com/rest/addLog"
        # 主线程休眠时间（可忽略，调试用）
        # self.sleep_time = float(settings.get("sleep_time")) if settings.get("sleep_time") else None

    def to_dict(self) -> dict:
        """将对象转换为字典"""
        return {
            "token": self.token,
            "aes_key": self.aes_key,
            "agent": {
                "app_id": self.agent_app_id,
                "files": self.agent_files,
                "inputs": self.agent_inputs,
                "type": self.selector_type,
            },
            # 修复：将不存在的agent_type_enum改为正确的agent_type
            "agent_type": self.agent_type,
            "is_auto_reply": self.is_auto_reply,
            "popo_app_key": self.popo_app_key,
            "popo_app_secret": self.popo_app_secret,
            "auto_reply_preset_message": self.auto_reply_preset_message,
            "workflow_input_field": self.workflow_input_field,
            "workflow_output_field": self.workflow_output_field
        }

    def __str__(self) -> str:
        """返回对象的JSON字符串表示"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def __repr__(self) -> str:
        """返回对象的字符串表示"""
        return self.__str__()