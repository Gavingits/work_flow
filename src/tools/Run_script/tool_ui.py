# -*- coding: utf-8 -*-
"""
Defines the Configuration UI for the Run_script Tool.
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QAbstractItemView,
                             QTableWidgetItem, QHeaderView, QDialog,
                             QDialogButtonBox, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt

class ConfigWidget(QWidget):
    """
    The configuration widget for the Run_script tool.
    Allows user to define key-value pairs for text replacement.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # List of dicts: [{'key': '...', 'value': '...'}]
        self.replacements = []
        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(QLabel("在模板脚本中替换文本:"))

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["待替换字符 (e.g., @VAR@)", "新字符"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_replacement)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_replacement)
        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self.remove_replacement)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)

    def _refresh_table(self):
        self.table.setRowCount(0)
        for item in self.replacements:
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)
            self.table.setItem(row_pos, 0, QTableWidgetItem(item['key']))
            self.table.setItem(row_pos, 1, QTableWidgetItem(item['value']))

    def add_replacement(self):
        dialog = EditReplacementDialog(self)
        if dialog.exec():
            key, value = dialog.get_data()
            if not key:
                QMessageBox.warning(self, "错误", "待替换字符不能为空。")
                return
            if any(r['key'] == key for r in self.replacements):
                QMessageBox.warning(self, "错误", f"待替换字符 '{key}' 已存在。")
                return
            self.replacements.append({'key': key, 'value': value})
            self._refresh_table()

    def edit_replacement(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return

        row_index = selected_rows[0].row()
        original_data = self.replacements[row_index]

        dialog = EditReplacementDialog(self, existing_data=original_data)
        if dialog.exec():
            new_key, new_value = dialog.get_data()
            if not new_key:
                QMessageBox.warning(self, "错误", "待替换字符不能为空。")
                return
            # Check for name collision only if the key was changed
            if original_data['key'] != new_key and any(r['key'] == new_key for r in self.replacements):
                QMessageBox.warning(self, "错误", f"待替换字符 '{new_key}' 已存在。")
                return

            self.replacements[row_index] = {'key': new_key, 'value': new_value}
            self._refresh_table()

    def remove_replacement(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return

        # Sort rows in descending order to avoid index shifting issues
        for row in sorted([r.row() for r in selected_rows], reverse=True):
            del self.replacements[row]
        self._refresh_table()

    def load_config(self, data):
        self.replacements = data.get('replacements', [])
        self._refresh_table()

    def get_config(self):
        return {'replacements': self.replacements}

class EditReplacementDialog(QDialog):
    def __init__(self, parent=None, existing_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加/编辑替换规则")
        layout = QVBoxLayout(self)

        self.key_edit = QLineEdit()
        self.value_edit = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("待替换字符:", self.key_edit)
        form_layout.addRow("新字符:", self.value_edit)
        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if existing_data:
            self.key_edit.setText(existing_data.get('key', ''))
            self.value_edit.setText(existing_data.get('value', ''))

    def get_data(self):
        return (self.key_edit.text().strip(), self.value_edit.text())
