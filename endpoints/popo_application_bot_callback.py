import json
import logging
import time
import traceback

from dify_plugin.config.config import InstallMethod
from dify_plugin.config.logger_format import plugin_logger_handler
import sys
from typing import Mapping

from werkzeug import Request, Response
from dify_plugin import Endpoint
import threading

from MyUtil import popo_bot_memory
from MyUtil.popo_application_bot_util import PopoBot
from MyUtil.popo_encryption_tool import AESCipher
from models.popo_bot_callback_structures import dict_to_robot_event, RobotEvent, PopoEventType
from models.popo_bot_endpoint_settings_structures import PopoBotEndpointSettings, GroupMessageReplyMethod, AgentType


# 日志，本地开发的使用用debug
logger = logging.getLogger(__name__)
if sys.platform in ('win32', 'cygwin', 'darwin'):
    is_dev = True
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
    is_dev = False
    logger.setLevel(logging.INFO)
    logger.addHandler(plugin_logger_handler)

# 定义 PopoBotToolEndpoint 类，继承自 Endpoint
class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        if logger.level == logging.DEBUG: self.session.install_method = InstallMethod.Remote
        try:
            plugin_settings = PopoBotEndpointSettings(settings)
            logger.debug("进入_invoke回调")
            self.session.storage.set("AAA","BBB".encode('utf-8'))
            # 非POPO回调时的连通性测试
            if not r.args:
                result = {
                    "备注": "端点连通性测试成功，插件使用方式请参考文档：https://docs.popo.netease.com/lingxi/4684e4335f894ab3a8a6b920adc71562"
                }
                result.update(plugin_settings.get_desensitized_settings())
                logger.debug("连通性测试成功")
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

            logger.debug(f"settings = {plugin_settings}")
            logger.debug(f"signature = {signature}, timestamp = {timestamp}, nonce = {nonce}, encrypt = {encrypt}")
            logger.debug("开始验证POPO签名")
            aes_cipher = AESCipher(plugin_settings.aes_key)
            ## 校验POPO签名   https://open.popo.netease.com/docs/robot/start/application-robot
            verify_result = aes_cipher.popo_check_signature(plugin_settings.token, timestamp, nonce, signature)
            if not verify_result:
                raise ValueError("校验签名验证失败")
            logger.debug(f"请求方法: {r.method}")
            # 处理来自POPO的不同类型请求，GET是保存回调配置时的校验，POST是消息订阅
            if r.method == "GET":
                logger.debug("收到GET请求")
                # GET时的解密验证去掉了，不知道什么原因导致可能解密失败
                # decrypt_text = aes_cipher.aes_cbc_decrypt(encrypt)
                # logger.debug("解密内容：", decrypt_text)
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
                logger.debug("收到POST请求")
                logger.debug(f"请求参数：{r.args}, 请求体：{r.data}")
                popo_message_encrypt = r.get_json().get("encrypt")
                if not popo_message_encrypt or popo_message_encrypt == "":
                    raise ValueError("POST响应中的数据未能成功解析到encrypt")
                try:
                    callback_message = json.loads(aes_cipher.aes_cbc_decrypt(popo_message_encrypt))
                    logger.debug(f"解密内容：{callback_message}")
                except Exception as e:
                    logging.error(f"解密失败: {str(e)}", exc_info=True)
                    raise

                robot_event = dict_to_robot_event(callback_message)
                popo_bot = PopoBot(plugin_settings.popo_app_key, plugin_settings.popo_app_secret)

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

                    # 清除记忆逻辑
                    clean_commands = {"@clean", "@清除记忆"}
                    notify_text = robot_event.event_data.notify.strip()
                    is_clean_command = (notify_text in clean_commands or
                                        any(notify_text.startswith(cmd) for cmd in clean_commands) or
                                        any(notify_text.endswith(cmd) for cmd in clean_commands))
                    if is_clean_command:
                        popo_bot.send_message(message_recipient, "重置对话流记忆，已开启新会话")
                        popo_bot_memory.clear_memory(robot_event, plugin_settings)
                        return Response(status=200)

                    # 预回复消息
                    if plugin_settings.auto_reply_preset_message:
                        popo_bot.send_message(message_recipient, plugin_settings.auto_reply_preset_message,robot_event.event_data.from_)
                    # 由于POPO方要求必须在三秒内响应，这里必须异步
                    logger.debug("开始异步调用智能体")

                    # thread = threading.Thread(
                    #     daemon=False,
                    #     target=self.call_agent,
                    #     kwargs={
                    #         "plugin_settings": plugin_settings,
                    #         "robot_event": robot_event,
                    #         "message_recipient":message_recipient,
                    #         "popo_bot":popo_bot
                    #     }
                    # )
                    #thread.start()
                    # 改成session提供的线程池执行
                    self.session._executor.submit(self.call_agent,plugin_settings,robot_event,message_recipient,popo_bot)
                    # 阻塞，防止session失效
                    time.sleep(1)
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
            # popo_bot.send_message(robot_event.event_data.from_,traceback.format_exc())
            return Response(
                json.dumps({"status": "error", "message": "处理请求失败", "error": str(e),"detailed_error":{traceback.format_exc()}}, ensure_ascii=False),
                status=500,
                content_type="application/json; charset=utf-8"
            )
    # 反向调用智能体
    def call_agent(self, plugin_settings: PopoBotEndpointSettings, robot_event: RobotEvent,message_recipient: str,popo_bot: PopoBot):
        logger.debug("异步调用智能体开始执行")
        try:
            logger.debug(f"调用智能体参数 - app_id: {plugin_settings.agent_app_id}")
            inputs_param = {
                "popo_input_message": robot_event.event_data.notify,
                "popo_user": robot_event.event_data.from_,
                "popo_event_type": robot_event.event_type.value,
                "popo_to": robot_event.event_data.to,
                "popo_msg_time": robot_event.event_data.addtime,
                "popo_raw_json": robot_event.raw_json,
            }
            if plugin_settings.agent_type == AgentType.WORKFLOW:
                inputs_param[plugin_settings.workflow_input_field] = robot_event.event_data.notify

            logger.debug(f"应用类型：{plugin_settings.agent_type}")
            if plugin_settings.agent_type in (AgentType.CHAT, AgentType.CHATFLOW):
                logger.debug("准备调用 chat.invoke")
                memory = popo_bot_memory.get_popobot_memory(robot_event, plugin_settings)
                logger.debug("没有找到记忆" if memory is None else "记忆："+str(memory.to_dict()))
                response = self.session.app.chat.invoke(
                    app_id=plugin_settings.agent_app_id,
                    inputs=inputs_param,
                    query=robot_event.event_data.notify,
                    response_mode="blocking",
                    conversation_id= "" if memory is None else memory.conversation_id
                )
                logger.debug("调用 chat.invoke 完成")
                popo_bot_memory.set_popobot_memory(robot_event,plugin_settings,response["conversation_id"])
                if not response:
                    raise ValueError("来自chat.invoke的空响应")
                else:
                    logger.debug(response)
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
            popo_bot.send_message(message_recipient,agent_output, robot_event.event_data.from_)
            logger.debug(f"回复结束，回复对象：{message_recipient}")

        except Exception as e:
            error_msg = f"调用智能体失败:\n{str(e)}\n详细错误信息:\n{traceback.format_exc()}"
            logging.error(error_msg, exc_info=True)
            popo_bot.send_message(robot_event.event_data.from_, error_msg)
            raise