from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from MyUtil.popo_application_bot_util import PopoBot


class SendPopoMessageTool(Tool):

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        app_key = tool_parameters.get("popo_app_key")
        app_secret = tool_parameters.get("popo_app_secret")
        receiver = tool_parameters.get("receiver")
        message = tool_parameters.get("message")
        at = tool_parameters.get("at")
        auto_convert_markdown_image_link = tool_parameters.get("auto_convert_markdown_image_link")

        popo_bot = PopoBot(app_key, app_secret)
        popo_bot.send_message(receiver, message, at,auto_convert_markdown_image_link)

        yield self.create_text_message("")
