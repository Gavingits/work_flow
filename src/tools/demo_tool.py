# -*- coding: utf-8 -*-
"""
A demonstration tool for the V2 workflow editor.
"""

def get_tool_definition():
    """
    Returns the definition of the tool's inputs and outputs.
    This is called by the main application to build the node's sockets.
    """
    return {
        'inputs': {
            'in_file': 'Path',
            'in_config': 'Json'
        },
        'outputs': {
            'out_log': 'Text',
            'out_data': 'Path'
        }
    }

def get_config_widget():
    """
    Returns a Qt Widget for configuring the tool.
    This is optional. If not provided, the node will not be configurable.
    """
    from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel("这是一个演示工具。\n它没有可用的配置选项。")
    layout.addWidget(label)
    return widget

def run(input_paths, output_paths, config_data):
    """
    The main execution function for the tool.
    Note: The signature now uses plural paths to support multiple
    inputs/outputs in the future. For now, we expect a dict with one entry.
    """
    print("--- 正在执行 Demo Tool ---")
    in_file = input_paths.get('in_file')
    out_log = output_paths.get('out_log')

    print(f"  输入文件: {in_file}")
    print(f"  输出日志: {out_log}")

    if not in_file:
        message = "Demo Tool: 未提供输入文件。"
    else:
        with open(in_file, 'r') as f:
            content = f.read(100)
            message = f"Demo Tool: 成功读取输入文件 '{in_file}' 的前100个字符。"
            print(f"    文件内容预览: {content}...")

    if out_log:
        with open(out_log, 'w') as f:
            f.write(message)

    print("--- Demo Tool 执行完毕 ---")
