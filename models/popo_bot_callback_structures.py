import json
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict

from dify_plugin.config.logger_format import plugin_logger_handler

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

# ------------------------------
# 事件类型枚举
# ------------------------------
class PopoEventType(Enum):
    """网易POPO机器人支持的事件类型枚举"""
    IM_P2P_TO_ROBOT_MSG = "IM_P2P_TO_ROBOT_MSG"  # 用户发送给机器人的单聊消息
    IM_CHAT_TO_ROBOT_AT_MSG = "IM_CHAT_TO_ROBOT_AT_MSG"  # 群组@机器人消息
    IM_P2P_USER_RECALL_MSG = "IM_P2P_USER_RECALL_MSG"  # 用户撤回单聊消息
    IM_CHAT_USER_RECALL_AT_MSG = "IM_CHAT_USER_RECALL_AT_MSG"  # 群组撤回@消息

    @classmethod
    def from_str(cls, event_type_str: str) -> "PopoEventType":
        """将接口返回的字符串转换为枚举成员（不存在则报错）"""
        for member in cls:
            if member.name == event_type_str:
                return member
        raise ValueError(f"不支持的事件类型: {event_type_str}")


# ------------------------------
# 通用子结构（无初始值，必须传入所有字段）
# ------------------------------
@dataclass
class QuoteInfo:
    """引用消息的详细信息（仅msgType=211时存在）"""
    file_name: Optional[str]  # 可选字段（可能为None）
    file_id: Optional[str]  # 可选字段（可能为None）
    from_user_name: Optional[str]
    reply_text: str  # 必选字段
    addtime: str  # 必选字段
    from_: str  # 必选字段（对应原字段from）
    uuid: str  # 必选字段
    notify: str  # 必选字段


@dataclass
class FileInfo:
    """文件消息的详细信息（仅msgType=171时存在）"""
    size: int  # 必选（文件大小，字节）
    name: str  # 必选（文件名）
    file_id: str  # 必选（文件ID）
    md5: str  # 必选（文件MD5）


@dataclass
class VideoInfo:
    """视频消息的详细信息（仅msgType=142时存在）"""
    cover_url: str  # 必选（封面URL）
    file_name: str  # 必选（视频文件名）
    size: int  # 必选（大小，字节）
    format: str  # 必选（格式，如mp4）
    width: int  # 必选（宽度）
    url: str  # 必选（视频URL）
    height: int  # 必选（高度）
    md5: str  # 必选（MD5）


@dataclass
class MergeListItem:
    """合并消息中的单条消息（仅msgType=161时存在）"""
    msg_type: int  # 必选（消息类型）
    addtime: str  # 必选（发送时间）
    session_type: int  # 必选（会话类型）
    from_: str  # 必选（发送者账号）
    to: str  # 必选（接收者账号）
    session_id: str  # 必选（会话ID）
    uuid: str  # 必选（消息唯一标识）
    notify: str  # 必选（消息内容）


# ------------------------------
# 不同事件类型对应的数据结构（无初始值）
# ------------------------------
@dataclass
class P2PMessageData:
    """用户发送给机器人的单聊消息数据（IM_P2P_TO_ROBOT_MSG）"""
    msg_type: int  # 必选（消息类型：1=文本，211=引用，等）
    addtime: str  # 必选（发送时间）
    session_type: int  # 必选（会话类型：1=单聊）
    robot_ids: List[str]  # 必选（机器人ID列表）
    from_: str  # 必选（发送者账号）
    to: str  # 必选（接收者账号，机器人账号）
    session_id: str  # 必选（会话ID）
    uuid: str  # 必选（消息唯一标识）
    notify: str  # 必选（消息内容/提示）
    # 以下为可选嵌套结构（根据msg_type决定是否存在）
    quote_info: Optional[QuoteInfo]
    file_info: Optional[FileInfo]
    video_info: Optional[VideoInfo]
    merge_list: Optional[List[MergeListItem]]
    merge_title: Optional[str]


@dataclass
class P2PRecallData:
    """用户撤回单聊消息的数据（IM_P2P_USER_RECALL_MSG）"""
    recall_time: str  # 必选（撤回时间）
    session_type: int  # 必选（会话类型）
    session_id: str  # 必选（会话ID）
    uuid: str  # 必选（被撤回消息的唯一标识）


@dataclass
class GroupRecallAtData:
    """群组用户撤回@机器人消息的数据（IM_CHAT_USER_RECALL_AT_MSG）"""
    uuid: str  # 必选（被撤回消息的唯一标识）
    addtime: str  # 必选（原消息发送时间）
    from_: str  # 必选（发送者账号）
    to: str  # 必选（群组ID）


@dataclass
class GroupAtData:
    """群组用户@机器人的消息数据（IM_CHAT_TO_ROBOT_AT_MSG）"""
    msg_type: int  # 必选（消息类型）
    session_id: str  # 必选（群组ID）
    uuid: str  # 必选（消息唯一标识）
    notify: str  # 必选（消息内容，含@信息）
    addtime: str  # 必选（发送时间）
    session_type: int  # 必选（会话类型：3=群组）
    from_: str  # 必选（发送者账号）
    to: str  # 必选（群组ID）
    at_type: int  # 必选（@类型：1=指定@）
    at_list: List[str]  # 必选（被@的机器人ID列表）


# ------------------------------
# 统一事件结构
# ------------------------------
@dataclass
class RobotEvent:
    """机器人接收的所有事件的统一结构"""
    event_type: PopoEventType  # 必选（事件类型枚举）
    event_data: P2PMessageData | P2PRecallData | GroupRecallAtData | GroupAtData  # 必选（对应事件的数据）
    raw_json: str # 原始JSON数据


# ------------------------------
# 转换函数（严格校验，缺失字段直接报错）
# ------------------------------
def dict_to_robot_event(data: Dict) -> RobotEvent:
    """
    将接口返回的字典转换为RobotEvent对象（无默认值，缺失字段直接报错）

    注意：若接口数据缺失任何必填字段，会直接抛出KeyError或TypeError
    """

    event_type = PopoEventType.from_str(data["eventType"])
    event_data_dict = data["eventData"]

    if event_type == PopoEventType.IM_P2P_TO_ROBOT_MSG:
        # 解析单聊消息（严格校验所有必选字段）
        quote_info = None
        if "quoteInfo" in event_data_dict:
            q = event_data_dict["quoteInfo"]
            quote_info = QuoteInfo(
                file_name=q.get("fileName"),
                file_id=q.get("fileId"),
                from_user_name=q["fromUserName"],
                reply_text=q["replyText"],
                addtime=q["addtime"],
                from_=q["from"],
                uuid=q["uuid"],
                notify=q["notify"]
            )

        file_info = None
        if "fileInfo" in event_data_dict:
            f = event_data_dict["fileInfo"]
            file_info = FileInfo(
                size=f["size"],
                name=f["name"],
                file_id=f["fileId"],
                md5=f["md5"]
            )

        video_info = None
        if "videoInfo" in event_data_dict:
            v = event_data_dict["videoInfo"]
            video_info = VideoInfo(
                cover_url=v["coverUrl"],
                file_name=v["fileName"],
                size=v["size"],
                format=v["format"],
                width=v["width"],
                url=v["url"],
                height=v["height"],
                md5=v["md5"]
            )

        merge_list = None
        if "mergeList" in event_data_dict:
            merge_list = [
                MergeListItem(
                    msg_type=item["msgType"],
                    addtime=item["addtime"],
                    session_type=item["sessionType"],
                    from_=item["from"],
                    to=item["to"],
                    session_id=item["sessionId"],
                    uuid=item["uuid"],
                    notify=item["notify"]
                )
                for item in event_data_dict["mergeList"]
            ]

        event_data = P2PMessageData(
            msg_type=event_data_dict["msgType"],
            addtime=event_data_dict["addtime"],
            session_type=event_data_dict["sessionType"],
            robot_ids=event_data_dict["robotIds"],
            from_=event_data_dict["from"],
            to=event_data_dict["to"],
            session_id=event_data_dict["sessionId"],
            uuid=event_data_dict["uuid"],
            notify=event_data_dict["notify"],
            quote_info=quote_info,
            file_info=file_info,
            video_info=video_info,
            merge_list=merge_list,
            merge_title=event_data_dict.get("mergeTitle")
        )

    elif event_type == PopoEventType.IM_P2P_USER_RECALL_MSG:
        event_data = P2PRecallData(
            recall_time=event_data_dict["recallTime"],
            session_type=event_data_dict["sessionType"],
            session_id=event_data_dict["sessionId"],
            uuid=event_data_dict["uuid"]
        )

    elif event_type == PopoEventType.IM_CHAT_USER_RECALL_AT_MSG:
        event_data = GroupRecallAtData(
            uuid=event_data_dict["uuid"],
            addtime=event_data_dict["addtime"],
            from_=event_data_dict["from"],
            to=event_data_dict["to"]
        )

    elif event_type == PopoEventType.IM_CHAT_TO_ROBOT_AT_MSG:
        event_data = GroupAtData(
            msg_type=event_data_dict["msgType"],
            session_id=event_data_dict["sessionId"],
            uuid=event_data_dict["uuid"],
            notify=event_data_dict["notify"],
            addtime=event_data_dict["addtime"],
            session_type=event_data_dict["sessionType"],
            from_=event_data_dict["from"],
            to=event_data_dict["to"],
            at_type=event_data_dict["atType"],
            at_list=event_data_dict["atList"]
        )

    else:
        raise ValueError(f"未处理的事件类型: {event_type}")

    return RobotEvent(event_type=event_type, event_data=event_data,raw_json=json.dumps(data, ensure_ascii=False, indent=2))


