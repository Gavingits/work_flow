# -*- coding: utf-8 -*-
"""
DOE Executor Tool for the Workflow Editor
"""
import os
import stat
import subprocess
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QSpinBox,
                             QDialog, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt

# --- Configuration Widget ---
class ConfigWidget(QWidget):
    """
    The configuration widget for the DOE Executor tool.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        layout = QFormLayout(self)
        self.parallel_jobs_spinbox = QSpinBox()
        self.parallel_jobs_spinbox.setRange(1, 128)
        self.parallel_jobs_spinbox.setValue(4)
        layout.addRow("最大并行任务数:", self.parallel_jobs_spinbox)

    def load_config(self, data):
        """Loads configuration from a dictionary."""
        self.parallel_jobs_spinbox.setValue(data.get('max_parallel_jobs', 4))

    def get_config(self):
        """Returns a dictionary with the current configuration."""
        return {
            'max_parallel_jobs': self.parallel_jobs_spinbox.value()
        }

# --- Tool Entry Points ---
def get_config_widget():
    """Main entry point for the host application to get the configuration UI."""
    return ConfigWidget()

def run(input_path, output_path, config_data):
    """
    Main entry point for the workflow execution.
    This function takes a doe_cases.csv file, finds the associated scripts,
    and executes them in parallel.
    """
    print("--- 开始执行 DOE Executor Tool ---")

    # --- 1. 参数校验 ---
    if not input_path or not Path(input_path).is_file():
        raise FileNotFoundError(f"输入文件 (doe_cases.csv) 未找到或无效: {input_path}")

    input_csv_path = Path(input_path)
    scripts_dir = input_csv_path.parent / f"{input_csv_path.stem}_scripts"

    if not scripts_dir.is_dir():
        raise NotADirectoryError(f"找不到对应的脚本目录: {scripts_dir}")

    max_jobs = config_data.get('max_parallel_jobs', 4)
    if max_jobs < 1:
        max_jobs = 1

    print(f"输入CSV: {input_csv_path}")
    print(f"脚本目录: {scripts_dir}")
    print(f"最大并行任务数: {max_jobs}")

    # --- 2. 生成执行脚本 (移植自原脚本) ---
    # This script is a runner that executes all .sp files in a given directory
    script_template = """#!/bin/bash
echo "开始执行HSPICE仿真..."
# These environment settings might need to be configured by the user
# or discovered in a more robust way in a real application.
# source /eda/common_tool/modules-v5.0.1/init/bash
# export SNPSLMD_LICENSE_FILE=27000@hzstor:27000@hzlc:27000@hzvml ic121
max_jobs={max_jobs_placeholder}
process_files() {{
    local dir_to_scan="$1"
    echo "正在处理目录: $dir_to_scan"
    local files=("$dir_to_scan"/*.sp)

    if [ ! -e "${{files[0]}}" ] ; then
        echo "在 $dir_to_scan 中未找到.sp文件"
        return
    fi

    for file in "${{files[@]}}"; do
        while [ $(jobs -rp | wc -l) -ge $max_jobs ]; do
            sleep 1
        done
        filename=$(basename "$file")
        output_file="$dir_to_scan/${{filename%.sp}}"
        echo "  正在启动: hspice $filename -o $output_file"
        # In a real scenario, the hspice command would be here.
        # For this example, we'll simulate the work by creating the output file.
        # bash -Is /path/to/hspice "$file" -o "$output_file" &
        echo "模拟仿真: $filename" > "$output_file.lis"
        sleep 0.1
    done
    wait
    echo "目录 $dir_to_scan 处理完毕。"
}}

process_files "{scripts_dir_placeholder}"

wait
echo "HSPICE仿真脚本执行完毕。"
"""
    # Replace placeholders
    final_script = script_template.format(
        max_jobs_placeholder=max_jobs,
        scripts_dir_placeholder=scripts_dir.resolve()
    )

    # --- 3. 保存并执行脚本 ---
    script_path = scripts_dir / "run_all_simulations.sh"
    try:
        script_path.write_text(final_script, encoding='utf-8')
        # Make the script executable
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        print(f"执行脚本已生成: {script_path}")

        # Execute the script using subprocess
        print(">>> 开始执行 run_all_simulations.sh...")
        # We use Popen to stream the output in real-time
        process = subprocess.Popen(
            ['bash', str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # Print output line by line
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())

        rc = process.poll()
        if rc != 0:
            raise subprocess.CalledProcessError(rc, cmd=str(script_path))

        print("<<< run_all_simulations.sh 执行成功。")

        # --- 4. 生成总结输出文件 ---
        summary_message = f"成功执行了 {scripts_dir.name} 中的所有仿真。\n"
        summary_message += f"并行任务数: {max_jobs}\n"
        summary_message += f"输入CSV: {input_csv_path.name}\n"

        output_path = Path(output_path)
        output_path.write_text(summary_message, encoding='utf-8')
        print(f"执行摘要已写入: {output_path}")

    except Exception as e:
        print(f"执行脚本时发生错误: {e}")
        # Propagate the error to the main workflow engine
        raise e

    print("--- DOE Executor Tool 执行完毕 ---")
