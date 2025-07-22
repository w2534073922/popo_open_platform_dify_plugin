import re
from enum import Enum, auto

import requests


class PopoMessageReceiverType(Enum):
    USER = auto()
    GROUP = auto()


def validate_receiver(receiver: str):
    # 邮箱格式验证正则表达式
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}$'
    # 群号格式验证正则表达式，5-10位数字
    group_pattern = r'^\d{5,10}$'

    # 先尝试验证是否为邮箱格式
    if re.match(email_pattern, receiver):
        return PopoMessageReceiverType.USER
    # 再尝试验证是否为群号格式
    elif re.match(group_pattern, receiver):
        return PopoMessageReceiverType.GROUP
    else:
        # 都不匹配时抛出异常
        raise ValueError("popo消息发送错误：无效的popo用户邮箱或群号")


class PopoBot:

    def __init__(self, aes_key, app_secret):
        self.appKey = aes_key
        self.app_secret = app_secret

    def send_message(self, receiver: str, message: str, auto_convert_markdown_image_link: bool = True) -> None:

        # 验证邮箱和群号格式
        validate_receiver(receiver)

        # 将markdown图片转换成popo所需的[img]xxx[/img]
        if auto_convert_markdown_image_link:
            pattern = r'!\[(.*?)]\(([^()]*(\([^()]*\)[^()]*)*)\)'
            message = re.sub(pattern, r'[img]\2[/img]', message)

        headers = {
            "Content-Type": "application/json",
            "Open-Access-Token": self.get_token(self.appKey, self.app_secret)
        }
        body = {
            "receiver": receiver,
            "message": {
                "content": [
                    {
                        "tag": "text",
                        "text": message
                    }
                ]
            },
            "msgType": "rich_text"
        }
        # 设置接口请求最大时间限制为5秒
        response = requests.post(
            "https://open.popo.netease.com/open-apis/robots/v1/im/send-msg",
            json=body,
            headers=headers,
            timeout=5
        )
        if response.status_code != 200 or response.json().get("errcode") != 0:
            if response.json().get("errmsg"):
                raise ValueError("popo消息发送错误：发送消息失败。errmsg：" + response.json().get("errmsg"))
            else:
                raise ValueError("popo消息发送错误：发送消息失败，未收到errmsg。")

    def get_token(self, app_key: str, app_secret: str) -> str:

        body = {
            "appKey": app_key,
            "appSecret": app_secret
        }
        # 添加 timeout=3 参数，设置接口请求最大时间限制为3秒
        response = requests.post(
            "https://open.popo.netease.com/open-apis/robots/v1/token",
            json=body,
            timeout=3
        )
        if response.status_code != 200 or response.json().get("errcode") != 0:
            if response.json().get("errmsg"):
                raise ValueError("popo消息发送错误：获取token失败。errmsg：" + response.json().get("errmsg"))
            else:
                raise ValueError("popo消息发送错误：获取token失败，未收到errmsg。")
        accessToken = response.json().get("data").get("accessToken")

        return accessToken

    # 邮箱和群号格式验证


if __name__ == '__main__':
    popo = PopoBot("AAAAAAtesTS0sA0Z1ahHsmG", "AAAAAAuWVeeauDnmtnh5rx7QrKxblJwmWjDF684aX27AHRSmtjIOOmRjjDKW7QoBFqi")
    popo.send_message("wb.wangfeng07@mesg.corp.netease.com", "老王真帅")
