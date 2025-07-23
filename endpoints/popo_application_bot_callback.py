import json
import logging
import time
from typing import Mapping

import requests
from dify_plugin.core.entities.invocation import InvokeType
from dify_plugin.core.runtime import BackwardsInvocation
from dify_plugin.invocations.app.chat import ChatAppInvocation
from werkzeug import Request, Response
from dify_plugin import Endpoint
import threading

from MyUtil.popo_encryption_tool import AESCipher

# 配置日志记录
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")


# 定义 PopoBotToolEndpoint 类，继承自 Endpoint
class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:

        # 通用后台任务执行方法
        def run_background_task(func, *args, **kwargs):
            """通用异步任务执行器

            Args:
                func: 要异步执行的函数
                *args: 函数位置参数
                **kwargs: 函数关键字参数
            """

            def _wrapper():
                try:
                    logging.debug("后台任务开始执行")
                    func(*args, **kwargs)
                    logging.debug("后台任务执行完成")
                except Exception as e:
                    logging.error(f"后台任务执行失败: {str(e)}", exc_info=True)

            thread = threading.Thread(target=_wrapper)
            thread.daemon = False
            thread.start()
            # 线程休眠，在difyCloud上似乎需要休眠才能正常运行
            # sleep_time = settings.get('sleep_time')
            # if sleep_time is not None:
            #     sleep_time = float(sleep_time)
            #     if 0 < sleep_time < 5:
            #         time.sleep(sleep_time)

        # popo方的query数据
        signature = r.args.get('signature')
        timestamp = r.args.get('timestamp')
        nonce = r.args.get('nonce')
        encrypt = r.args.get('encrypt')  # get请求时才有这个参数
        # 插件参数
        token = settings["token"]
        aes_key = settings["aesKey"]
        agent_type = settings["agent_type"]

        logging.debug(f"signature = {signature}, timestamp = {timestamp}, nonce = {nonce}, encrypt = {encrypt}")
        logging.debug(f"token = {token} , aesKey = {aes_key}, agent_type = {agent_type}")
        aes_cipher = AESCipher(aes_key)
        ## 校验POPO签名   https://open.popo.netease.com/docs/robot/start/application-robot
        verify_result = aes_cipher.popo_check_signature(token, timestamp, nonce, signature)
        if not verify_result:
            print("校验签名验证失败")
            raise ValueError("校验签名验证失败")

        # 处理来自POPO的不同类型请求，GET是保存回调配置时的校验，POST是消息订阅
        if r.method == "GET":
            # GET时的解密验证去掉了，不知道什么原因导致可能解密失败
            # decrypt_text = aes_cipher.aes_cbc_decrypt(encrypt)
            # logging.debug("解密内容：", decrypt_text)
            response_content = {
                "success": aes_cipher.aes_cbc_encrypt("success")
            }
            response = Response(
                json.dumps(response_content, ensure_ascii=False),
                status=200,
                content_type="application/json; charset=utf-8"
            )
            return response
        elif r.method == "POST":
            logging.debug("收到POST请求")
            logging.debug(f"请求参数：{r.args}, 请求体：{r.data}")
            popo_message_encrypt = r.get_json().get("encrypt")
            if not popo_message_encrypt or popo_message_encrypt == "":
                raise ValueError("POST响应中的数据未能成功解析到encrypt")
            try:
                popo_message_json = json.loads(aes_cipher.aes_cbc_decrypt(popo_message_encrypt))
                logging.debug(f"解密内容：{popo_message_json}")
            except Exception as e:
                logging.error(f"解密失败: {str(e)}", exc_info=True)
                raise

            # popo消息和发送的用户
            popo_message_content = popo_message_json["eventData"]["notify"]
            popo_user = popo_message_json["eventData"]["from"]
            popo_to = popo_message_json["eventData"]["to"]
            popo_event_type = popo_message_json["eventType"]

            # 转发给智能体，启动通用后台任务
            app_id = settings['agent']["app_id"]
            run_background_task(
                self.call_agent,  # 要异步执行的函数
                app_id,  # 函数参数
                settings,
                popo_message_content,
                popo_user,
                popo_to,
                popo_event_type,
                agent_type
            )
            return Response(
                status=200,
            )
        else:
            return Response(
                json.dumps({"status": "error", "message": "不支持的请求方法"}, ensure_ascii=False),
                status=405,
                content_type="application/json; charset=utf-8"
            )

    # 反向调用智能体
    def call_agent(self, app_id, settings: Mapping, popo_message_content: str, popo_user: str, popo_to: str,
                   popo_event_type: str, agent_type: str):
        logging.debug("异步调用智能体开始执行")
        # self.send_log("异步调用智能体已执行，智能体id：" + app_id, settings)
        try:
            # 添加参数校验
            if not app_id or not isinstance(app_id, str):
                raise ValueError("应用id无效")

            # 添加详细的参数日志
            logging.info(f"调用智能体参数 - app_id: {app_id}")

            inputs_param = {
                "popo_message_content": popo_message_content,  # 工作流没有默认的query参数所以需要将消息作为inputs参数
                "popo_user": popo_user,
                "popo_event_type": popo_event_type,
                "popo_to": popo_to,
            }

            if agent_type == "chat" or agent_type == "chatflow":

                response = self.session.app.chat.invoke(
                    app_id=app_id,
                    inputs=inputs_param,
                    query=popo_message_content,
                    response_mode="blocking",
                    conversation_id=""  # 可选，留空则创建新对话
                )
            elif agent_type == "workflow":
                response = self.session.app.workflow.invoke(
                    app_id=app_id,
                    inputs=inputs_param,
                    response_mode="blocking",
                )
            else:
                raise ValueError("不支持的智能体类型")

            # 添加响应验证
            if not response:
                raise ValueError("来自chat.invoke的空响应")

            # 工作流可能没有返回值，所以不考虑空答复的情况。
            # answer = response.get("answer")
            # if not answer:
            #     raise ValueError("空的回答")

            # self.send_log("异步调用智能体已返回，结果：" + answer, settings)

        except Exception as e:
            error_msg = f"调用智能体失败: {str(e)}"
            logging.error(error_msg, exc_info=True)
            # self.send_log(error_msg, settings)
            raise

    # 上报日志到接口，目前已经废弃
    def send_log(self, log, settings: Mapping):
        logReportingAddress = settings.get('logReportingAddress', '')
        if not logReportingAddress:  # 空字符串或 None 都为 False
            logReportingAddress = 'https://log-jystudy.app.codewave.163.com/rest/addLog'
        # 请求体数据
        payload = {
            "group": "popo_bot_plugin",
            "log": log
        }

        # 发送POST请求
        try:
            requests.post(logReportingAddress, data=json.dumps(payload), headers={"Content-Type": "application/json"})
        except Exception as e:
            logging.error(f"发送日志失败: {str(e)}", exc_info=True)
