import json
import logging
import time
from typing import Mapping

import requests
from werkzeug import Request, Response
from dify_plugin import Endpoint
import threading

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# 定义 PopoBotToolEndpoint 类，继承自 Endpoint


class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        print("settings是"+str(settings))
        print(settings['agent']["app_id"])
        app_id = settings['agent']["app_id"]
        logging.info(f"app_id是:{app_id}")

        ##启动通用后台任务
        self.run_background_task(
            self.call_agent,  # 要异步执行的函数
            app_id,            # 函数参数
            settings
        )
        # self.call_agent(app_id, settings)
        logging.info("任务已启动")

        # 生成 JSON 格式的响应内容
        response_content = {
            "status": "success",
            "message": "请求方法为：" + r.method,
            "task_status": "running"
        }
        return Response(
            json.dumps(response_content, ensure_ascii=False),
            status=200,
            content_type="application/json; charset=utf-8"
        )

    # 通用后台任务执行方法（支持任意函数和参数）
    def run_background_task(self, func, *args, **kwargs):
        """通用异步任务执行器
        
        Args:
            func: 要异步执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
        """
        def _wrapper():
            try:
                logging.info("后台任务开始执行")
                func(*args, **kwargs)
                logging.info("后台任务执行完成")
            except Exception as e:
                logging.error(f"后台任务执行失败: {str(e)}", exc_info=True)
                
        thread = threading.Thread(target=_wrapper)
        thread.daemon = False
        thread.start()
        time.sleep(0.8)


    # 调用智能体（保持原有业务逻辑不变）
    def call_agent(self, app_id, settings: Mapping):
        self.send_log("异步调用智能体已执行，智能体id："+app_id, settings)
        try:
            # 添加参数校验
            if not app_id or not isinstance(app_id, str):
                raise ValueError("应用id无效")

            # 添加详细的参数日志
            logging.info(f"调用智能体参数 - app_id: {app_id}")
            
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
            self.send_log("异步调用智能体已返回，结果："+answer, settings)
            
        except Exception as e:
            error_msg = f"调用智能体失败: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.send_log(error_msg, settings)  # <<== 增加settings参数传递
            raise

    def send_log(self,log,settings: Mapping):
        print("sendlog函数里的settings是"+str(settings))
        logReportingAddress = settings.get('logReportingAddress', '')
        if not logReportingAddress:  # 空字符串或 None 都为 False
            logReportingAddress = 'https://dev-log-jystudy.app.codewave.163.com/rest/addLog'
        # 请求体数据
        payload = {
            "group": "popo_bot_plugin",
            "log": log
        }

        # 发送POST请求
        requests.post(logReportingAddress, data=json.dumps(payload), headers={"Content-Type": "application/json"})

    # 向popo用户发消息
    # def send_popobot_message(self, message,email):