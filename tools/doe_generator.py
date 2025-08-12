# -*- coding: utf-8 -*-
"""
DOE Generator Tool for the Workflow Editor
"""
import itertools
import re
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import pyDOE2
except ImportError:
    # This will be caught by the main app's execution handler
    raise ImportError("pyDOE2 library is required. Please run 'pip install pyDOE2'")

from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QAbstractItemView,
                             QTableWidgetItem, QHeaderView, QComboBox,
                             QDialog, QDialogButtonBox, QFormLayout,
                             QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt

# --- Helper Functions ---
def _smart_convert(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

def _format_value(value):
    if isinstance(value, (int, float)) and float(value) == int(value):
        return str(int(value))
    return str(value)

# --- Main Configuration Widget ---
class ConfigWidget(QWidget):
    """
    The main configuration widget for the DOE Generator tool.
    This UI is displayed in a dialog when the user double-clicks the node.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.variables = {}  # {name: {name, type, values_list, values_str}}
        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)

        # --- DOE Method ---
        form_layout = QFormLayout()
        self.doe_method_combo = QComboBox()
        self.doe_method_combo.addItems(["全因子设计 (Full Factorial)", "中心复合设计 (CCD)"])
        form_layout.addRow("设计方法:", self.doe_method_combo)
        layout.addLayout(form_layout)

        # --- Variables Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["变量名", "类型", "取值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_variable)
        layout.addWidget(self.table)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加变量")
        add_btn.clicked.connect(self.add_variable)
        edit_btn = QPushButton("编辑选中变量")
        edit_btn.clicked.connect(self.edit_variable)
        remove_btn = QPushButton("删除选中变量")
        remove_btn.clicked.connect(self.remove_variable)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)

    def _refresh_table(self):
        self.table.setRowCount(0)
        for name, var_data in sorted(self.variables.items()):
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(name))
            self.table.setItem(row_position, 1, QTableWidgetItem(var_data['type']))
            self.table.setItem(row_position, 2, QTableWidgetItem(var_data['values_str']))

    def add_variable(self):
        dialog = AddVariableDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_data()
            if result['name'] in self.variables:
                QMessageBox.warning(self, "错误", f"变量 '{result['name']}' 已存在。")
                return
            self.variables[result['name']] = result
            self._refresh_table()

    def edit_variable(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            # Check if a cell is selected
            if not self.table.currentItem():
                 QMessageBox.information(self, "提示", "请选择一个变量进行编辑。")
                 return
            row_index = self.table.currentItem().row()
        else:
            row_index = selected_rows[0].row()

        var_name = self.table.item(row_index, 0).text()
        original_data = self.variables[var_name]

        dialog = AddVariableDialog(self, existing_data=original_data)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            # If name changed, handle rename
            if var_name != new_data['name']:
                if new_data['name'] in self.variables:
                    QMessageBox.warning(self, "错误", f"变量名 '{new_data['name']}' 已存在。")
                    return
                del self.variables[var_name]
            self.variables[new_data['name']] = new_data
            self._refresh_table()

    def remove_variable(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请选择要删除的变量。")
            return

        var_name = self.table.item(selected_rows[0].row(), 0).text()
        if QMessageBox.question(self, "确认删除", f"确定要删除变量 '{var_name}' 吗？") == QMessageBox.Yes:
            del self.variables[var_name]
            self._refresh_table()

    def load_config(self, data):
        """Loads configuration from a dictionary."""
        self.doe_method_combo.setCurrentText(data.get('doe_method', "全因子设计 (Full Factorial)"))
        self.variables = data.get('variables', {})
        self._refresh_table()

    def get_config(self):
        """Returns a dictionary with the current configuration."""
        return {
            'doe_method': self.doe_method_combo.currentText(),
            'variables': self.variables
        }

# --- Helper Dialog for Add/Edit Variable ---
class AddVariableDialog(QDialog):
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加/编辑变量")

        self.layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["离散变量", "连续变量"])
        self.values_edit = QLineEdit()

        self.layout.addRow("变量名:", self.name_edit)
        self.layout.addRow("类型:", self.type_combo)
        self.layout.addRow("取值 (用逗号分隔):", self.values_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        if existing_data:
            self.name_edit.setText(existing_data['name'])
            self.type_combo.setCurrentText(existing_data['type'])
            self.values_edit.setText(existing_data['values_str'])

    def get_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'values_str': self.values_edit.text().strip(),
        }

# --- Tool Entry Points ---
def get_config_widget():
    """Main entry point for the host application to get the configuration UI."""
    return ConfigWidget()

def run(input_path, output_path, config_data):
    """Main entry point for the workflow execution."""
    print("--- 开始执行 DOE Generator Tool ---")

    template_path = Path(input_path)
    output_csv_path = Path(output_path)
    output_dir = output_csv_path.parent

    # --- 1. 参数校验 ---
    if not template_path.is_file():
        raise FileNotFoundError(f"模板文件未找到: {template_path}")

    variables = config_data.get('variables', {})
    if not variables:
        raise ValueError("未定义任何变量。请在节点配置中定义变量。")

    doe_method = config_data.get('doe_method', "全因子设计 (Full Factorial)")

    print(f"模板: {template_path}")
    print(f"输出CSV: {output_csv_path}")
    print(f"设计方法: {doe_method}")

    # --- 2. 解析模板，获取有效变量 ---
    try:
        template_content = template_path.read_text(encoding='utf-8')
        template_vars = set(re.findall(r'@(\w+)@', template_content))
    except Exception as e:
        raise IOError(f"读取模板文件失败: {e}")

    active_vars = {}
    for name, data in variables.items():
        if name in template_vars:
            try:
                values_str = data['values_str']
                if data['type'] == '连续变量':
                    parts = [p.strip() for p in values_str.split(',')]
                    if len(parts) != 3: raise ValueError("连续变量必须有3个值 (min, typ, max)")
                    values_list = [_smart_convert(p) for p in parts]
                else:
                    values_list = [p.strip() for p in values_str.split(',') if p.strip()]

                active_vars[name] = {'values_list': values_list, 'type': data['type']}
            except ValueError as e:
                raise ValueError(f"变量 '{name}' 的取值 '{values_str}' 格式错误: {e}")

    if not active_vars:
        raise ValueError("所有定义的变量都未在模板文件中找到。")
    print(f"有效变量: {', '.join(sorted(active_vars.keys()))}")

    # --- 3. 执行DOE算法 ---
    final_df = pd.DataFrame()
    if doe_method == "全因子设计 (Full Factorial)":
        sorted_names = sorted(active_vars.keys())
        value_lists = [active_vars[name]['values_list'] for name in sorted_names]
        final_df = pd.DataFrame(list(itertools.product(*value_lists)), columns=sorted_names)
    elif doe_method == "中心复合设计 (CCD)":
        ccd_vars = {k: v for k, v in active_vars.items() if v['type'] == '连续变量'}
        if not ccd_vars:
            raise ValueError("CCD设计需要至少一个连续变量。")

        k = len(ccd_vars)
        ccd_names = sorted(ccd_vars.keys())

        # Note: pyDOE2 ccdesign has limitations. This is a simplified mapping.
        # Levels: -1, 0, 1
        coded_matrix = pyDOE2.ccdesign(k, center=(1, 1), face='ccc')

        plan = []
        for coded_row in coded_matrix:
            real_row = {}
            for i, name in enumerate(ccd_names):
                min_v, typ_v, max_v = ccd_vars[name]['values_list']
                coded_val = coded_row[i]
                if coded_val == 0:
                    real_row[name] = typ_v
                elif coded_val > 0: # Map positive alpha to max
                    real_row[name] = max_v
                else: # Map negative alpha to min
                    real_row[name] = min_v
            plan.append(real_row)
        final_df = pd.DataFrame(plan, columns=ccd_names)

    final_df = final_df.round(4)

    # --- 4. 生成脚本并保存CSV ---
    scripts_dir = output_dir / f"{output_csv_path.stem}_scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    def generate_filename(row, index):
        parts = [template_path.stem]
        for name, value in row.items():
            formatted_value = _format_value(value).replace('.', 'p').replace('-', 'n')
            parts.append(f"{name}_{formatted_value}")
        return "_".join(parts) + ".sp" # Assuming .sp extension

    filenames = [generate_filename(row, i) for i, row in final_df.iterrows()]
    final_df.insert(0, 'output_filename', filenames)

    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    print(f"成功生成DOE Case清单: {output_csv_path} ({len(final_df)} cases)")

    for index, row in final_df.iterrows():
        case_content = template_content
        for var_name in active_vars.keys():
            case_content = case_content.replace(f"@{var_name}@", _format_value(row[var_name]))

        script_path = scripts_dir / row['output_filename']
        script_path.write_text(case_content, encoding='utf-8')

    print(f"成功生成 {len(final_df)} 个脚本文件于目录: {scripts_dir}")
    print("--- DOE Generator Tool 执行完毕 ---")
