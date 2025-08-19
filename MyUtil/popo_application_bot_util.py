import re
from enum import Enum, auto
import requests
from cachetools import TTLCache, cached


class PopoMessageReceiverType(Enum):
    USER = auto()
    GROUP = auto()


class PopoBot:
    # 类级别的缓存，所有实例共享，实现单例缓存效果
    _token_cache = TTLCache(maxsize=200, ttl=21600)  # token缓存六个小时

    def __init__(self, app_key, app_secret):
        self.appKey = app_key
        self.app_secret = app_secret

    @classmethod
    @cached(_token_cache)  # 使用类级别的缓存
    def get_token(cls, app_key: str, app_secret: str) -> str:
        """类方法，所有实例共享缓存"""
        body = {
            "appKey": app_key,
            "appSecret": app_secret
        }
        response = requests.post(
            "https://open.popo.netease.com/open-apis/robots/v1/token",
            json=body,
            timeout=3
        )
        if response.status_code != 200 or response.json().get("errcode") != 0:
            errmsg = response.json().get("errmsg", "未收到错误信息")
            raise ValueError(f"popo消息发送错误：获取token失败。errmsg：{errmsg}")
        return response.json().get("data").get("accessToken")

    def validate_receiver(self, receiver: str) -> PopoMessageReceiverType:
        """移到类内部作为实例方法"""
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}$'
        group_pattern = r'^\d{5,10}$'

        if re.match(email_pattern, receiver):
            return PopoMessageReceiverType.USER
        elif re.match(group_pattern, receiver):
            return PopoMessageReceiverType.GROUP
        else:
            raise ValueError("popo消息发送错误：无效的popo用户邮箱或群号")

    def send_message(self, receiver: str, message: str, auto_convert_markdown_image_link: bool = True) -> None:
        self.validate_receiver(receiver)

        if auto_convert_markdown_image_link:
            pattern = r'!\[(.*?)]\(([^()]*(\([^()]*\)[^()]*)*)\)'
            message = re.sub(pattern, r'[img]\2[/img]', message)

        headers = {
            "Content-Type": "application/json",
            # 调用类方法获取token
            "Open-Access-Token": self.get_token(self.appKey, self.app_secret)
        }
        body = {
            "receiver": receiver,
            "message": {
                "content": [{"tag": "text", "text": message}]
            },
            "msgType": "rich_text"
        }

        response = requests.post(
            "https://open.popo.netease.com/open-apis/robots/v1/im/send-msg",
            json=body,
            headers=headers,
            timeout=5
        )
        if response.status_code != 200 or response.json().get("errcode") != 0:
            errmsg = response.json().get("errmsg", "未收到错误信息")
            raise ValueError(f"popo消息发送错误：发送消息失败。errmsg：{errmsg}")


if __name__ == '__main__':
    popo1 = PopoBot("AAA", "BBB")
    popo2 = PopoBot("AAA", "BBB")

    # 两个实例会共享同一个token缓存
    popo1.send_message("wb.wangfeng07@mesg.corp.netease.com", "老王真帅")
    popo2.send_message("wb.wangfeng07@mesg.corp.netease.com", "老王真帅2")
