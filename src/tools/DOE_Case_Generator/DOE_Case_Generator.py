# -*- coding: utf-8 -*-
"""
Main entry point and execution logic for the DOE_Case_Generator tool.
"""
import itertools
import re
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import pyDOE2
except ImportError:
    raise ImportError("pyDOE2 library is required. Please run 'pip install pyDOE2'")

# Import the UI component from the sibling file
from .tool_ui import ConfigWidget

def get_tool_definition():
    """Defines the inputs and outputs of this tool."""
    return {
        'inputs': {'template_file': 'Path'},
        'outputs': {'output_floader': 'Directory'}
    }

def get_config_widget():
    """Returns the configuration widget for this tool."""
    return ConfigWidget()

def _smart_convert(s):
    try: return int(s)
    except ValueError: return float(s)

def _format_value(value):
    if isinstance(value, (int, float)) and float(value) == int(value):
        return str(int(value))
    return str(value)

def _parse_values(value_str):
    """
    Parses the user-provided value string, handling special syntax.
    - Expands ranges like 'xx1-3' -> ['xx1', 'xx2', 'xx3']
    - Handles single-run selection with '#' prefix.
    """
    # Handle single-run selection
    if '#' in value_str:
        for part in value_str.split(','):
            part = part.strip()
            if part.startswith('#'):
                return [part[1:]] # Return only the marked value
        return [] # Should not happen if # is present

    # Handle range expansion
    final_parts = []
    for part in value_str.split(','):
        part = part.strip()
        match = re.match(r'([a-zA-Z_]+)(\d+)-(\d+)', part)
        if match:
            prefix, start, end = match.groups()
            start, end = int(start), int(end)
            for i in range(start, end + 1):
                final_parts.append(f"{prefix}{i}")
        else:
            final_parts.append(part)
    return final_parts

def run(input_paths, output_paths, config_data):
    """Main execution function for the DOE generator."""
    print("--- 开始执行 DOE_Case_Generator ---")

    template_file = input_paths.get('template_file')
    output_folder = output_paths.get('output_floader') # This is a file path inside the temp dir

    if not template_file:
        raise ValueError("输入 'template_file' 未连接或无效。")
    if not output_folder:
        raise ValueError("内部错误: 未提供 'output_floader' 路径。")

    template_path = Path(template_file)
    # The actual output folder is the directory containing the socket file
    output_dir = Path(output_folder).parent
    output_dir.mkdir(exist_ok=True)

    variables = config_data.get('variables', {})
    if not variables: raise ValueError("未定义任何变量。")

    template_content = template_path.read_text(encoding='utf-8')
    template_vars = set(re.findall(r'@(\w+)@', template_content))

    active_vars = {name: data for name, data in variables.items() if name in template_vars}
    if not active_vars: raise ValueError("所有定义的变量都未在模板文件中找到。")

    # Process variables for DOE and Full Factorial
    doe_vars = {}
    ff_vars = {}
    for name, data in active_vars.items():
        parsed_list = _parse_values(data['values_str'])
        if not parsed_list:
            raise ValueError(f"变量 '{name}' 的取值 '{data['values_str']}' 解析后为空。")

        var_info = {'values_list': parsed_list, 'type': data['type']}

        if data.get('is_doe', False) and data['type'] == 'continuous':
            if len(var_info['values_list']) != 3:
                raise ValueError(f"用于DOE的连续变量 '{name}' 必须有3个值 (min,typ,max)。")
            var_info['values_list'] = [_smart_convert(v) for v in var_info['values_list']]
            doe_vars[name] = var_info
        else:
            ff_vars[name] = var_info

    # Generate plans
    df_ff = pd.DataFrame([{}])
    if ff_vars:
        ff_names = sorted(ff_vars.keys())
        ff_lists = [ff_vars[name]['values_list'] for name in ff_names]
        df_ff = pd.DataFrame(list(itertools.product(*ff_lists)), columns=ff_names)

    df_doe = pd.DataFrame([{}])
    if doe_vars:
        k = len(doe_vars)
        doe_names = sorted(doe_vars.keys())
        coded_matrix = pyDOE2.ccdesign(k, center=(1, 1), face='ccc')
        plan = []
        for coded_row in coded_matrix:
            real_row = {}
            for i, name in enumerate(doe_names):
                min_v, typ_v, max_v = doe_vars[name]['values_list']
                coded_val = coded_row[i]
                if coded_val == 0: real_row[name] = typ_v
                elif coded_val > 0: real_row[name] = max_v
                else: real_row[name] = min_v
            plan.append(real_row)
        df_doe = pd.DataFrame(plan, columns=doe_names)

    # Merge plans
    final_df = df_ff.assign(key=1).merge(df_doe.assign(key=1), on='key').drop('key', axis=1)
    final_df = final_df.round(4)

    # Generate filenames and scripts
    scripts_subdir = output_dir / "doe_scripts"
    scripts_subdir.mkdir(exist_ok=True)

    def generate_filename(row, index):
        style = config_data.get('filename_style', '详细 (变量_值)')
        if style == '简洁 (case_序号)':
            return f"{template_path.stem}_case{index + 1}{template_path.suffix}"

        parts = [template_path.stem]
        for name, value in row.items():
            parts.append(f"{name}_{_format_value(value).replace('.', 'p').replace('-', 'n')}")
        return "_".join(parts) + template_path.suffix

    filenames = [generate_filename(row, i) for i, row in final_df.iterrows()]
    final_df.insert(0, 'output_filename', filenames)

    for index, row in final_df.iterrows():
        content = template_content
        for col in final_df.columns:
            if col != 'output_filename':
                content = content.replace(f"@{col}@", _format_value(row[col]))
        (scripts_subdir / row['output_filename']).write_text(content, encoding='utf-8')

    # Save the main case list CSV
    output_csv_path = Path(output_folder) # The socket path is the CSV
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')

    print(f"成功生成 {len(final_df)} 个Case到: {output_csv_path}")
    print(f"成功生成 {len(final_df)} 个脚本文件于: {scripts_subdir}")
    print("--- DOE_Case_Generator 执行完毕 ---")
