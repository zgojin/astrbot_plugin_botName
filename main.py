import os
import psutil
import yaml
import logging
import datetime
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.all import *

logger = logging.getLogger(__name__)

# 插件目录
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_botName')
# 确保插件目录存在
if not os.path.exists(PLUGIN_DIR):
    os.makedirs(PLUGIN_DIR)

# 系统信息文件路径
SYSTEM_INFO_FILE = os.path.join(PLUGIN_DIR, 'system_info.yml')
# 名片模板文件路径
NAME_TEMPLATE_FILE = os.path.join(PLUGIN_DIR, 'name.yml')

def read_yaml_file(file_path):
    encodings = ['utf-8', 'gbk', 'iso-8859-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return yaml.safe_load(file)
        except UnicodeDecodeError:
            logger.warning(f"使用 {encoding} 编码读取文件 {file_path} 失败，尝试下一个编码。")
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"读取 YAML 文件 {file_path} 时出错: {e}")
            return None
    logger.error(f"无法使用可用编码读取文件 {file_path}。")
    return None

class SystemInfoRecorder:
    def __init__(self, file_path):
        self.file_path = file_path

    def record_system_info(self):
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        # 只保留小时和分钟
        current_time = datetime.datetime.now().strftime("%H:%M")
        system_info = {
            "cpu_usage": cpu_percent,
            "memory_usage": memory_percent,
            "current_time": current_time
        }
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                yaml.dump(system_info, file)
            logger.info("系统信息已成功保存到 YAML 文件。")
        except Exception as e:
            logger.error(f"保存系统信息到 YAML 文件时出错: {e}")

@register("dynamic_group_card", "Your Name", "动态群名片插件", "1.0.0", "repo url")
class DynamicGroupCardPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.info_recorder = SystemInfoRecorder(SYSTEM_INFO_FILE)
        # 用于存储每个群聊的最后修改时间
        self.group_last_modify_time = {}

    @filter.on_decorating_result()
    async def modify_card_before_send(self, event: AstrMessageEvent):
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            group_id = event.message_obj.group_id

            if group_id:
                now = datetime.datetime.now()
                # 获取该群聊的最后修改时间，如果不存在则为 None
                last_modify_time = self.group_last_modify_time.get(group_id)

                # 检查距离上一次修改是否已经过了一分钟
                if last_modify_time is None or (now - last_modify_time).total_seconds() >= 60:
                    # 每次发消息时记录系统信息
                    self.info_recorder.record_system_info()

                    system_info = read_yaml_file(SYSTEM_INFO_FILE)
                    if system_info is None:
                        cpu_usage = "未知"
                        memory_usage = "未知"
                        current_time = "未知"
                    else:
                        cpu_usage = system_info.get("cpu_usage", "未知")
                        memory_usage = system_info.get("memory_usage", "未知")
                        current_time = system_info.get("current_time", "未知")

                    template = read_yaml_file(NAME_TEMPLATE_FILE)
                    if template is None:
                        card_format = "脑容量占用 {cpu_usage}%，内存占用 {memory_usage}%，当前时间 {current_time}"
                    else:
                        card_format = template.get('card_format', "脑容量占用 {cpu_usage}%，内存占用 {memory_usage}%，当前时间 {current_time}")

                    new_card = card_format.format(cpu_usage=cpu_usage, memory_usage=memory_usage, current_time=current_time)

                    payload = {
                        "group_id": group_id,
                        "user_id": event.message_obj.self_id,
                        "card": new_card
                    }

                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            result = await client.api.call_action('set_group_card', **payload)
                            logger.info(f"成功尝试修改群 {group_id} 中Bot的群名片为 {new_card}，API返回: {result}")
                            # 更新该群聊的最后修改时间
                            self.group_last_modify_time[group_id] = now
                            break
                        except Exception as e:
                            if retry < max_retries - 1:
                                logger.warning(f"修改群 {group_id} 中Bot的群名片时出错，第 {retry + 1} 次重试: {e}")
                            else:
                                logger.error(f"修改群 {group_id} 中Bot的群名片时出错，重试 {max_retries} 次后失败: {e}")
