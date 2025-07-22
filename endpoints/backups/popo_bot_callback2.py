import asyncio
import json
import time
import logging
import requests
import threading
from werkzeug import Request, Response
from dify_plugin import Endpoint

# 配置日志记录
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_log(log):
    url = "https://dev-log-jystudy.app.codewave.163.com/rest/addLog"
    payload = {
        "group": "popo_bot_plugin",
        "log": log
    }
    response = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    return response

class PopoBotToolEndpoint(Endpoint):
    def _invoke(self, r: Request, values: dict, settings: dict) -> Response:
        app_id = settings['agent']["app_id"]
        logging.info(f"app_id是: {app_id}")

        # 启动后台任务
        self.run_background_task(self.call_agent, app_id)
        logging.info("后台任务已启动")

        # 立即响应请求
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

    def run_background_task(self, func, *args, **kwargs):
        async def _async_wrapper():
            try:
                logging.info("后台任务开始执行")
                await func(*args, **kwargs)  # 保留原始参数传递
                logging.info("后台任务执行完成")
            except Exception as e:
                logging.error(f"后台任务执行失败: {str(e)}", exc_info=True)
        
        # 线程安全的事件循环管理
        def _thread_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_async_wrapper())
            finally:
                loop.close()

        thread = threading.Thread(target=_thread_target)
        thread.daemon = False  # 确保任务完成
        thread.start()

    async def call_agent(self, app_id):  # 改为异步方法
        logging.info("异步调用智能体开始执行")
        send_log("异步调用智能体已执行，智能体 id：" + app_id)
        response = await self.session.app.chat.invoke(  # 添加 await 关键字
            app_id=app_id,
            inputs={},
            query=f"这是来自插件的 query 参数，时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
            response_mode="blocking",
            conversation_id=""
        )
        answer = response.get("answer")
        logging.info(f"智能体返回的答案：{answer}")
        send_log("异步调用智能体已返回，结果：" + str(answer))