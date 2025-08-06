import os
import psutil
import yaml
import logging
import datetime
from astrbot.api import AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.all import *

logger = logging.getLogger(__name__)

# 插件目录
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_botname')
# 确保插件目录存在
if not os.path.exists(PLUGIN_DIR):
    os.makedirs(PLUGIN_DIR)

# 系统信息文件路径
SYSTEM_INFO_FILE = os.path.join(PLUGIN_DIR, 'system_info.yml')

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

@register("astrbot_plugin_botname", "长安某", "bot动态群名片插件", "2.0.0", "https://github.com/zgojin/astrbot_plugin_botname")
class DynamicGroupCardPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.info_recorder = SystemInfoRecorder(SYSTEM_INFO_FILE)
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
                last_modify_time = self.group_last_modify_time.get(group_id)

                if last_modify_time is None or (now - last_modify_time).total_seconds() >= 60:
                    self.info_recorder.record_system_info()

                    system_info = read_yaml_file(SYSTEM_INFO_FILE)
                    if system_info is None:
                        cpu_usage, memory_usage, current_time = "未知", "未知", "未知"
                    else:
                        cpu_usage = system_info.get("cpu_usage", "未知")
                        memory_usage = system_info.get("memory_usage", "未知")
                        current_time = system_info.get("current_time", "未知")

                    # *** 核心改动：使用前缀和后缀动态构建群名片 ***
                    
                    metric_parts = []
                    
                    # CPU 部分
                    cpu_prefix = self.config.get('cpu_prefix', '')
                    cpu_suffix = self.config.get('cpu_suffix', '')
                    if cpu_prefix or cpu_suffix: # 只要前缀或后缀有一个不为空，就显示
                        metric_parts.append(f"{cpu_prefix}{cpu_usage}{cpu_suffix}")
                        
                    # 内存部分
                    mem_prefix = self.config.get('memory_prefix', '')
                    mem_suffix = self.config.get('memory_suffix', '')
                    if mem_prefix or mem_suffix:
                        metric_parts.append(f"{mem_prefix}{memory_usage}{mem_suffix}")

                    # 时间部分
                    time_prefix = self.config.get('time_prefix', '')
                    time_suffix = self.config.get('time_suffix', '')
                    if time_prefix or time_suffix:
                        metric_parts.append(f"{time_prefix}{current_time}{time_suffix}")

                    # 用分隔符拼接所有指标
                    separator = self.config.get('separator', ' | ')
                    metrics_string = separator.join(metric_parts)

                    # 添加机器人名字
                    bot_name = self.config.get('bot_name', '')
                    
                    # 组合最终的群名片
                    final_card_parts = []
                    if bot_name:
                        final_card_parts.append(bot_name)
                    if metrics_string:
                        final_card_parts.append(metrics_string)
                    
                    new_card = " ".join(final_card_parts).strip()
                    
                    # 如果最终生成的名片为空（所有配置都为空），则不执行修改
                    if not new_card:
                        logger.info(f"群 {group_id} 的群名片所有配置项均为空，跳过修改。")
                        return

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
                            self.group_last_modify_time[group_id] = now
                            break
                        except Exception as e:
                            if retry < max_retries - 1:
                                logger.warning(f"修改群 {group_id} 中Bot的群名片时出错，第 {retry + 1} 次重试: {e}")
                            else:
                                logger.error(f"修改群 {group_id} 中Bot的群名片时出错，重试 {max_retries} 次后失败: {e}")
