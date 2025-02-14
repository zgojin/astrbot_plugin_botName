# astrbot_plugin_botName

让机器人学会自己改名片

# 功能
在bot进行发言时，获取系统当前cpu占用率，内存占用率，以及当前时间，随后对名片修改
# 使用
###  安装依赖库

本插件依赖 `psutil` 和 `PyYAML` 这两个 Python 库，你可以使用 `pip`（Python 包管理工具）来完成安装。

- **Windows**：按下 `Win + R` 组合键，输入 `cmd` 后回车，即可打开命令提示符窗口；或者在开始菜单中搜索“命令提示符”并打开。
- **macOS**：打开“应用程序”文件夹，找到“实用工具”文件夹，双击“终端”应用程序。
- **Linux**：不同发行版打开终端的方式可能不同，常见的是使用快捷键 `Ctrl + Alt + T` 或者在应用程序菜单里找到“终端”打开。
####  执行安装命令

在命令行中输入以下命令并回车：

```bash
pip install psutil PyYAML
```
也可能是

```bash
pip3 install psutil PyYAML
```
### 配置
你需要修改`name.yml` 文件
这个文件的作用是定义群名片的显示格式。你可以根据自己的需求，自由地组合 `{cpu_usage}`、`{memory_usage}` 和 `{current_time}` 这三个参数，并且还能添加自定义的文本内容。以下是一个示例：
```yaml
# 这是群名片的格式模板，你可以根据需求自由组合以下参数：
# {cpu_usage}: 系统的 CPU 使用率，以百分比形式呈现
# {memory_usage}: 系统的内存使用率，以百分比形式呈现
# {current_time}: 当前的系统时间，格式为 HH:MM
card_format: "cpu占用 {cpu_usage}%，内存占用 {memory_usage}%，时间 {current_time}"
