import json
import logging
import time
from typing import Mapping

import requests
from torch.utils.hipify.hipify_python import mapping
from werkzeug import Request, Response
from dify_plugin import Endpoint
import threading

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


# 定义 PopoBotToolEndpoint 类，继承自 Endpoint
class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:

        # 调用智能体（保持原有业务逻辑不变）
        def call_agent():
            logging.info("异步调用智能体开始执行")
            #self.send_log("异步调用智能体已执行，智能体id：" + app_id, settings)
            try:
                # 添加参数校验
                if not app_id or not isinstance(app_id, str):
                    raise ValueError("应用id无效")

                # 添加详细的参数日志
                logging.info(f"调用智能体参数 - app_id: {app_id}")
                # self.session.session_id = self.session.session_id[::-1]
                # logging.info(f"倒置的session_id: {self.session.session_id}")
                # newSession = copy.copy(self.session)
                # response = newSession.app.chat.invoke(
                response = self.session.app.chat.invoke(
                    app_id=app_id,
                    inputs={},
                    query=f"这是来自插件的query参数，时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
                    response_mode="blocking",
                    conversation_id=""  # 可选，留空则创建新对话
                )

                # 添加响应验证
                if not response:
                    raise ValueError("来自chat.invoke的空响应")

                answer = response.get("answer")
                if not answer:
                    raise ValueError("空的回答")

                print(answer)
                #self.send_log("异步调用智能体已返回，结果：" + answer, settings)

            except Exception as e:
                error_msg = f"调用智能体失败: {str(e)}"
                logging.error(error_msg, exc_info=True)
                #self.send_log(error_msg, settings)
                raise

        def send_log(log):
            pass
            #print("sendlog函数里的settings是" + str(settings))
            # log_reporting_address = settings.get('logReportingAddress', '')
            # if not log_reporting_address:  # 空字符串或 None 都为 False
            #     log_reporting_address = 'https://dev-log-jystudy.app.codewave.163.com/rest/addLog'
            # # 请求体数据
            # payload = {
            #     "group": "popo_bot_plugin",
            #     "log": log
            # }
            #
            # # 发送POST请求
            # requests.post(log_reporting_address, data=json.dumps(payload), headers={"Content-Type": "application/json"})

        print("settings是" + str(settings))
        app_id = settings['agent']["app_id"]
        logging.info(f"app_id是:{app_id}")

        # 创建线程并启动
        thread = threading.Thread(target=call_agent)
        thread.daemon = False
        thread.start()

        sleep_time = mapping.get('sleep_time')
        if sleep_time is not None:
            sleep_time = float(sleep_time)
        if 0 < sleep_time < 5:
            time.sleep(sleep_time)

        # 生成 JSON 格式的响应内容
        response_content = {
            "status": "success",
            "message": "请求方法为：" + r.method,
            "task_status": "completed"
        }
        return Response(
            json.dumps(response_content, ensure_ascii=False),
            status=200,
            content_type="application/json; charset=utf-8"
        )
