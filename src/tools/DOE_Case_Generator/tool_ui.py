# -*- coding: utf-8 -*-
"""
Defines the Configuration UI for the DOE_Case_Generator Tool.
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QAbstractItemView,
                             QTableWidgetItem, QHeaderView, QComboBox,
                             QDialog, QDialogButtonBox, QFormLayout,
                             QMessageBox, QCheckBox, QHBoxLayout)
from PyQt6.QtCore import Qt

class ConfigWidget(QWidget):
    """
    The configuration widget for the DOE_Case_Generator tool.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.variables = {}
        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # --- DOE Method ---
        form_layout = QFormLayout()
        self.doe_method_combo = QComboBox()
        self.doe_method_combo.addItems(["全因子设计 (Full Factorial)", "中心复合设计 (CCD)"])
        form_layout.addRow("DOE 设计方法:", self.doe_method_combo)

        self.filename_style_combo = QComboBox()
        self.filename_style_combo.addItems(["详细 (变量_值)", "简洁 (case_序号)"])
        form_layout.addRow("生成文件名风格:", self.filename_style_combo)

        layout.addLayout(form_layout)

        # --- Variables Table ---
        layout.addWidget(QLabel("变量定义 (勾选 'DOE' 列以应用选择的DOE方法):"))
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["DOE", "变量名", "类型", "取值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_variable)
        layout.addWidget(self.table)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        add_btn = QPushButton("添加变量")
        add_btn.clicked.connect(self.add_variable)
        edit_btn = QPushButton("编辑选中")
        edit_btn.clicked.connect(self.edit_variable)
        remove_btn = QPushButton("删除选中")
        remove_btn.clicked.connect(self.remove_variable)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)

    def _refresh_table(self):
        self.table.setRowCount(0)
        for name, var_data in sorted(self.variables.items()):
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            # Checkbox for DOE selection
            doe_check = QCheckBox()
            doe_check.setChecked(var_data.get('is_doe', False))
            doe_check.stateChanged.connect(lambda state, n=name: self.variables[n].__setitem__('is_doe', state == Qt.CheckState.Checked.value))
            self.table.setCellWidget(row_pos, 0, doe_check)

            self.table.setItem(row_pos, 1, QTableWidgetItem(name))
            self.table.setItem(row_pos, 2, QTableWidgetItem(var_data['type']))
            self.table.setItem(row_pos, 3, QTableWidgetItem(var_data['values_str']))

    def add_variable(self):
        dialog = AddVariableDialog(self)
        if dialog.exec():
            result = dialog.get_data()
            if not result['name']:
                QMessageBox.warning(self, "错误", "变量名不能为空。")
                return
            if result['name'] in self.variables:
                QMessageBox.warning(self, "错误", f"变量 '{result['name']}' 已存在。")
                return
            self.variables[result['name']] = result
            self._refresh_table()

    def edit_variable(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            if not self.table.currentItem(): return
            row_index = self.table.currentItem().row()
        else:
            row_index = selected_rows[0].row()

        var_name = self.table.item(row_index, 1).text()
        original_data = self.variables[var_name]

        dialog = AddVariableDialog(self, existing_data=original_data)
        if dialog.exec():
            new_data = dialog.get_data()
            if var_name != new_data['name']:
                if new_data['name'] in self.variables:
                    QMessageBox.warning(self, "错误", f"变量名 '{new_data['name']}' 已存在。")
                    return
                del self.variables[var_name]
            self.variables[new_data['name']] = new_data
            self._refresh_table()

    def remove_variable(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return
        var_name = self.table.item(selected_rows[0].row(), 1).text()
        if QMessageBox.question(self, "确认删除", f"确定要删除变量 '{var_name}' 吗？") == QMessageBox.StandardButton.Yes:
            del self.variables[var_name]
            self._refresh_table()

    def load_config(self, data):
        """Loads configuration from a dictionary passed by the main app."""
        self.doe_method_combo.setCurrentText(data.get('doe_method', "全因子设计 (Full Factorial)"))
        self.filename_style_combo.setCurrentText(data.get('filename_style', "详细 (变量_值)"))
        self.variables = data.get('variables', {})
        self._refresh_table()

    def get_config(self):
        """Returns a dictionary with the current UI state."""
        # The checkbox state is updated directly on the self.variables dict
        return {
            'doe_method': self.doe_method_combo.currentText(),
            'filename_style': self.filename_style_combo.currentText(),
            'variables': self.variables
        }

class AddVariableDialog(QDialog):
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加/编辑变量")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["discrete", "continuous"])
        self.values_edit = QLineEdit()
        self.values_edit.setToolTip("离散值用逗号分隔 (e.g., 1,2,3)。\n"
                                  "连续值格式为 min,typ,max (e.g., 1,5,9)。\n"
                                  "范围缩写 xxA-B 会被展开 (e.g., cdb1-3 -> cdb1,cdb2,cdb3)。\n"
                                  "用 # 前缀标记某个值为本次运行的唯一值。")

        layout.addRow("变量名 (name):", self.name_edit)
        layout.addRow("类型 (type):", self.type_combo)
        layout.addRow("取值 (values):", self.values_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if existing_data:
            self.name_edit.setText(existing_data['name'])
            self.type_combo.setCurrentText(existing_data['type'])
            self.values_edit.setText(existing_data['values_str'])

    def get_data(self):
        # is_doe is handled in the main widget's table
        return {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'values_str': self.values_edit.text().strip(),
        }
