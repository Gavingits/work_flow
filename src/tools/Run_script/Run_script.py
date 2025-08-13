# -*- coding: utf-8 -*-
"""
Main entry point and execution logic for the Run_script tool.
"""
import os
import stat
import shutil
import subprocess
from pathlib import Path

# Import the UI component from the sibling file
from .tool_ui import ConfigWidget

def get_tool_definition():
    """Defines the inputs and outputs of this tool."""
    return {
        'inputs': {'script_template_file': 'Path'},
        'outputs': {'output_floader': 'Directory'} # Actually outputs a file inside this
    }

def get_config_widget():
    """Returns the configuration widget for this tool."""
    return ConfigWidget()

def run(input_paths, output_paths, config_data):
    """
    Replaces text in a template script, saves it, and runs it in a new terminal.
    """
    print("--- 开始执行 Run_script ---")

    template_file = input_paths.get('script_template_file')
    output_folder_socket = output_paths.get('output_floader')

    if not template_file:
        raise ValueError("输入 'script_template_file' 未连接或无效。")
    if not output_folder_socket:
        raise ValueError("内部错误: 未提供 'output_floader' 路径。")

    template_path = Path(template_file)
    output_dir = Path(output_folder_socket).parent
    output_dir.mkdir(exist_ok=True)

    # 1. Read template content
    try:
        content = template_path.read_text(encoding='utf-8')
    except Exception as e:
        raise IOError(f"读取模板文件 '{template_path}'失败: {e}")

    # 2. Perform replacements
    replacements = config_data.get('replacements', [])
    for item in replacements:
        content = content.replace(item['key'], item['value'])

    # 3. Save the new script
    new_script_name = f"{template_path.stem}_modified{template_path.suffix}"
    new_script_path = output_dir / new_script_name
    try:
        new_script_path.write_text(content, encoding='utf-8')
        # Make the script executable
        new_script_path.chmod(new_script_path.stat().st_mode | stat.S_IEXEC)
        print(f"已生成新脚本: {new_script_path}")
    except Exception as e:
        raise IOError(f"保存新脚本失败: {e}")

    # 4. Run the new script in a new terminal
    # This logic is adapted from the user's original Tkinter example.
    terminals = [
        ('gnome-terminal', '--'),
        ('konsole', '-e'),
        ('xfce4-terminal', '--command='),
        ('x-terminal-emulator', '-e'),
        ('xterm', '-e')
    ]

    found_terminal = False
    for term, flag in terminals:
        if shutil.which(term):
            try:
                # Command to run the script and then wait for user input to close
                command_to_run = (
                    f'echo "正在运行脚本: {new_script_path.name}...";'
                    f'echo "----------------------------------------";'
                    f'bash "{new_script_path}";'
                    f'echo "----------------------------------------";'
                    f'echo; echo "--- 脚本执行完毕 ---";'
                    f'echo "按 Enter 键关闭此终端。";'
                    f'read'
                )

                # Different terminals have different ways of passing commands
                if '=' in flag:
                    cmd_list = [term, f"{flag}bash -c '{command_to_run}'"]
                else:
                    cmd_list = [term, flag, "bash", "-c", command_to_run]

                print(f"找到终端 '{term}', 尝试执行...")
                subprocess.Popen(cmd_list)
                found_terminal = True
                break
            except Exception as e:
                print(f"尝试使用 '{term}' 失败: {e}")

    if not found_terminal:
        raise RuntimeError("未能找到任何可用的终端程序 (如 gnome-terminal, konsole, xterm)。")

    # 5. Write to the output socket file to signal completion
    # The main output is the new script itself. We can write its path to the socket file.
    Path(output_folder_socket).write_text(str(new_script_path), encoding='utf-8')

    print("--- Run_script 执行完毕 ---")
