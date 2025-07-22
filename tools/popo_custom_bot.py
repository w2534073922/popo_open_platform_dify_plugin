import base64
import hashlib
import hmac
import json
import re
import time

from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
import requests


class SendPopoMessageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        webhook_url = tool_parameters.get("webhook_url")
        message = tool_parameters.get("message")
        secret = tool_parameters.get("secret")
        auto_convert_markdown_image_link = tool_parameters.get("auto_convert_markdown_image_link")
        send_result = send_message(webhook_url, message, secret, auto_convert_markdown_image_link)

        yield self.create_text_message(str(send_result))


def send_message(webhook_url: str, message: str, secret: str, auto_convert_markdown_image_link: bool = True):
    """
    发送消息到POPO自定义机器人

    :param auto_convert_markdown_image_link: 自动将markdown图片格式转换成popo所需的格式
    :param webhook_url: 机器人 webhook 地址（形如 https://open.popo.netease.com/...）
    :param message: 要发送的消息内容
    :param secret: 签名校验的密钥
    """

    # 将markdown图片转换成popo所需的[img]xxx[/img]
    if auto_convert_markdown_image_link:
        pattern = r'!\[(.*?)]\(([^()]*(\([^()]*\)[^()]*)*)\)'
        message = re.sub(pattern, r'[img]\2[/img]', message)

    headers = {"Content-Type": "application/json"}
    payload = {"message": message}

    if secret:
        # 生成时间戳（毫秒级）
        timestamp = int(time.time() * 1000)
        payload["timestamp"] = str(timestamp)

        # 生成签名
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign_data = base64.b64encode(hmac_code).decode("utf-8")
        payload["signData"] = sign_data

    response = requests.post(
        webhook_url,
        headers=headers,
        data=json.dumps(payload)
    )
    response.raise_for_status()  # 检查 HTTP 错误状态码
    result = response.json()
    # 如果errcode不为0，则抛出异常

    if result.get("errcode") != 0:
        raise Exception(f"消息发送失败，错误码：{result.get('errcode')}，错误信息：{result.get('errmsg')}")
    return result


if __name__ == '__main__':
    WEBHOOK_URL = "https://open.popo.netease.com/open-apis/robots/v1/hook/9NNIFVCGkiLIHu7ZiocdO44j2gwb17Mw0Erh2BMQHiUHxtzUP4YpZjIMI460SeST2pDY3ZSswCWM843f4sdKvhL0J5faFhTl"
    # 示例 1：不启用签名校验（仅发送消息）
    send_message(
        webhook_url=WEBHOOK_URL,
        message="你好，这是一条测试消息haha",
        secret=""
    )
