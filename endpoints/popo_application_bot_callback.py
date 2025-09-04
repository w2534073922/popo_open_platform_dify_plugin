import json
import logging
import sys
from typing import Mapping

from werkzeug import Request, Response
from dify_plugin import Endpoint
import threading

from MyUtil.popo_application_bot_util import PopoBot
from MyUtil.popo_encryption_tool import AESCipher
from models.popo_bot_callback_structures import dict_to_robot_event, RobotEvent, PopoEventType
from models.popo_bot_endpoint_settings_structures import PopoBotEndpointSettings, GroupMessageReplyMethod, AgentType

# 本地开发时，Windows和Mac会是debug级别日志
if sys.platform in ('win32', 'cygwin', 'darwin'):
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


# 定义 PopoBotToolEndpoint 类，继承自 Endpoint
class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        try:
            plugin_settings = PopoBotEndpointSettings(settings)
            logging.debug("进入_invoke回调")
            if r.args.get("debug") == 'true' and r.args.get('signature') is None:
                result = plugin_settings.get_desensitized_settings()
                result.update({
                    "endpointStatus": "端点连通性测试成功"
                })
                return Response(
                    json.dumps(result, ensure_ascii=False),
                    status=200,
                    content_type="application/json; charset=utf-8"
                )
            # popo方的query数据
            signature = r.args.get('signature')
            timestamp = r.args.get('timestamp')
            nonce = r.args.get('nonce')
            encrypt = r.args.get('encrypt')  # get请求时才有这个参数

            logging.debug(f"settings = {plugin_settings}")
            logging.debug(f"signature = {signature}, timestamp = {timestamp}, nonce = {nonce}, encrypt = {encrypt}")
            logging.debug("开始验证POPO签名")
            aes_cipher = AESCipher(plugin_settings.aes_key)
            ## 校验POPO签名   https://open.popo.netease.com/docs/robot/start/application-robot
            verify_result = aes_cipher.popo_check_signature(plugin_settings.token, timestamp, nonce, signature)
            if not verify_result:
                raise ValueError("校验签名验证失败")
            logging.debug(f"请求方法: {r.method}")
            # 处理来自POPO的不同类型请求，GET是保存回调配置时的校验，POST是消息订阅
            if r.method == "GET":
                logging.debug("收到GET请求")
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
                    callback_message = json.loads(aes_cipher.aes_cbc_decrypt(popo_message_encrypt))
                    logging.debug(f"解密内容：{callback_message}")
                except Exception as e:
                    logging.error(f"解密失败: {str(e)}", exc_info=True)
                    raise

                robot_event = dict_to_robot_event(callback_message)
                if robot_event.event_type in (PopoEventType.IM_P2P_TO_ROBOT_MSG, PopoEventType.IM_CHAT_TO_ROBOT_AT_MSG):
                    # 私聊or群聊
                    if robot_event.event_type == PopoEventType.IM_P2P_TO_ROBOT_MSG:
                        message_recipient = robot_event.event_data.from_
                    elif robot_event.event_type == PopoEventType.IM_CHAT_TO_ROBOT_AT_MSG:
                        # 收到群@时的回复策略
                        if plugin_settings.group_message_reply_method == GroupMessageReplyMethod.GROUP_CHAT:
                            message_recipient = robot_event.event_data.to
                        else:
                            message_recipient = robot_event.event_data.from_
                    # 预回复消息
                    if plugin_settings.auto_reply_preset_message:
                        popo_bot = PopoBot(plugin_settings.popo_app_key, plugin_settings.popo_app_secret)
                        popo_bot.send_message(message_recipient, plugin_settings.auto_reply_preset_message,robot_event.event_data.from_)
                    # 由于POPO方要求必须在三秒内响应，这里必须异步
                    logging.debug("开始异步调用智能体")
                    thread = threading.Thread(
                        daemon=False,
                        target=self.call_agent,
                        kwargs={
                            "plugin_settings": plugin_settings,
                            "robot_event": robot_event,
                            "message_recipient":message_recipient
                        }
                    )
                    thread.start()
                return Response(
                    status=200,
                )
            else:
                return Response(
                    json.dumps({"status": "error", "message": "不支持的请求方法"}, ensure_ascii=False),
                    status=405,
                    content_type="application/json; charset=utf-8"
                )
        except Exception as e:
            logging.error(f"invoke执行异常: {str(e)}", exc_info=True)
            return Response(
                json.dumps({"status": "error", "message": "处理请求失败", "error": str(e)}, ensure_ascii=False),
                status=500,
                content_type="application/json; charset=utf-8"
            )
    # 反向调用智能体
    def call_agent(self, plugin_settings: PopoBotEndpointSettings, robot_event: RobotEvent,message_recipient: str):
        logging.debug("异步调用智能体开始执行")
        try:

            logging.debug(f"调用智能体参数 - app_id: {plugin_settings.agent_app_id}")
            inputs_param = {
                "popo_input_message": robot_event.event_data.notify,
                "popo_user": robot_event.event_data.from_,
                "popo_event_type": robot_event.event_type.value,
                "popo_to": robot_event.event_data.to,
                "popo_raw_json": robot_event.raw_json,
            }
            if plugin_settings.agent_type == AgentType.WORKFLOW:
                inputs_param[plugin_settings.workflow_input_field] = robot_event.event_data.notify

            logging.debug(f"应用类型：{plugin_settings.agent_type}")
            if plugin_settings.agent_type in (AgentType.CHAT, AgentType.CHATFLOW):
                logging.debug("准备调用 chat.invoke")
                response = self.session.app.chat.invoke(
                    app_id=plugin_settings.agent_app_id,
                    inputs=inputs_param,
                    query=robot_event.event_data.notify,
                    response_mode="blocking",
                    conversation_id=""  # 可选，留空则创建新对话
                )
                logging.debug("调用 chat.invoke 完成")
                if not response:
                    raise ValueError("来自chat.invoke的空响应")
                else:
                    logging.debug(response)
                    agent_output = response["answer"]

            elif plugin_settings.agent_type == AgentType.WORKFLOW:
                response = self.session.app.workflow.invoke(
                    app_id=plugin_settings.agent_app_id,
                    inputs=inputs_param,
                    response_mode="blocking",
                )
                if not response:
                    raise ValueError("来自chat.invoke的空响应")

                if response["data"]["status"] != "succeeded":
                    raise ValueError("工作流未正常执行")
                else:
                    agent_output = response["data"]["outputs"][plugin_settings.workflow_output_field]

            else:
                raise ValueError("不支持的智能体类型")
            popo_bot = PopoBot(plugin_settings.popo_app_key, plugin_settings.popo_app_secret)
            popo_bot.send_message(message_recipient,agent_output, robot_event.event_data.from_)
            logging.debug(f"回复结束，回复对象：{message_recipient}")

        except Exception as e:
            error_msg = f"调用智能体失败:\n {str(e)}"
            logging.error(error_msg, exc_info=True)
            popo_bot = PopoBot(plugin_settings.popo_app_key, plugin_settings.popo_app_secret)
            popo_bot.send_message(robot_event.event_data.from_, error_msg)
            raise

    # 上报日志到接口，目前已经废弃
    # def send_log(self, log: str, settings: Mapping):
    #     logReportingAddress = settings.get('logReportingAddress', '')
    #     if not logReportingAddress:  # 空字符串或 None 都为 False
    #         logReportingAddress = 'https://log-jystudy.app.codewave.163.com/rest/addLog'
    #     # 请求体数据
    #     payload = {
    #         "group": "popo_bot_plugin",
    #         "log": log
    #     }
    #
    #     # 发送POST请求
    #     try:
    #         requests.post(logReportingAddress, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    #     except Exception as e:
    #         logging.error(f"发送日志失败: {str(e)}", exc_info=True)