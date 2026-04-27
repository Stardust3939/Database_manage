import sys
import re
import datetime
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QLabel, QHeaderView, QFileDialog, QMessageBox, 
                             QFrame, QAbstractItemView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# [span_0](start_span)[span_1](start_span)基础配置与逻辑映射[span_0](end_span)[span_1](end_span)
BASE32_CHARS = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
PREFIX_MAP = {'K': '0', 'L': '1', 'U': '2'}

class ClinicalDataApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("临床数据录入系统")
        self.resize(1300, 850)
        self.setup_ui()
        self.add_new_row() # 默认添加起始行

    def setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # [span_2](start_span)头部：标题与主按钮 [cite: 7-8, 55]
        header_layout = QHBoxLayout()
        title_label = QLabel("临床数据录入系统")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        
        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("添加行")
        self.import_btn = QPushButton("导入Excel")
        self.export_btn = QPushButton("导出Excel")
        self.reset_btn = QPushButton("重置")
        
        # [cite_start]按钮样式美化 [cite: 20-28]
        button_style = "QPushButton { padding: 8px 15px; font-weight: bold; border-radius: 4px; }"
        self.add_row_btn.setStyleSheet(button_style + "background-color: #27ae60; color: white;")
        self.export_btn.setStyleSheet(button_style + "background-color: #3498db; color: white;")
        self.import_btn.setStyleSheet(button_style + "background-color: #3498db; color: white;")
        self.reset_btn.setStyleSheet(button_style + "background-color: #e74c3c; color: white;")

        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.reset_btn)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(btn_layout)
        self.main_layout.addLayout(header_layout)

        # [cite_start]前缀设置区[span_2](end_span)
        prefix_frame = QFrame()
        prefix_frame.setStyleSheet("background-color: #e8f4fd; border-radius: 8px; border: 1px solid #b8daff;")
        prefix_layout = QHBoxLayout(prefix_frame)
        prefix_layout.addWidget(QLabel("分子号前缀："))
        self.prefix_combo = QComboBox()
        self.prefix_combo.addItems(["K", "L", "U"])
        prefix_layout.addWidget(self.prefix_combo)
        self.apply_prefix_btn = QPushButton("应用并更新所有分子号")
        prefix_layout.addWidget(self.apply_prefix_btn)
        prefix_layout.addWidget(QLabel("(统一前缀，数字部分保持4位)"))
        prefix_layout.addStretch()
        self.main_layout.addWidget(prefix_frame)

        # [span_3](start_span)数据表格[span_3](end_span)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["操作", "姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code"])
        
        # --- 解决双击痛点：设置为单击即可编辑 ---
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.AnyKeyPressed | 
            QAbstractItemView.EditTrigger.SelectedClicked | 
            QAbstractItemView.EditTrigger.CurrentChanged
        )
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table)

        # [span_4](start_span)统计栏[span_4](end_span)
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("总记录数: 0")
        self.male_label = QLabel("男性: 0")
        self.female_label = QLabel("女性: 0")
        for lbl in [self.total_label, self.male_label, self.female_label]:
            lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            stats_layout.addWidget(lbl)
        self.main_layout.addLayout(stats_layout)

        # 信号连接
        self.add_row_btn.clicked.connect(self.add_new_row)
        self.export_btn.clicked.connect(self.export_to_excel)
        self.import_btn.clicked.connect(self.import_from_excel)
        self.reset_btn.clicked.connect(self.reset_data)
        self.apply_prefix_btn.clicked.connect(self.apply_prefix_to_all)
        self.table.cellChanged.connect(self.handle_cell_changed)

    # --- 核心算法逻辑 ---

    def to_base32(self, num):
        [span_5](start_span)"""将分子号数字转为32进制 [cite: 69-72]"""
        if num == 0: return '000'
        res = ''
        n = num
        while n > 0:
            res = BASE32_CHARS[n % 32] + res
            n //= 32
        return res.rjust(3, '0')

    def get_month_code(self, month):
        [cite_start]"""月份转码 [cite: 73-74]"""
        if 1 <= month <= 9: return str(month)
        codes = {10: 'A', 11: 'B', 12: 'C'}
        return codes.get(month, '0')

    def get_next_molecular_number(self):
        """基于当前表格最大值自动递增"""
        prefix = self.prefix_combo.currentText()
        max_num = 0
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 4) # 分子号列
            if item and item.text():
                match = re.search(r'(\d{4})$', item.text())
                if match:
                    num = int(match.group(1))
                    if num > max_num: max_num = num
        return f"{prefix}{max_num + 1:04d}"

    def calculate_row_code(self, row):
        [cite_start]"""生成12位Code逻辑 [cite: 76-81]"""
        try:
            # 1. 分子号Base32 (前3位)
            mol_item = self.table.item(row, 4)
            mol_text = mol_item.text() if mol_item else ""
            match = re.search(r'\d{4}$', mol_text)
            num = int(match.group()) if match else 0
            part1 = self.to_base32(num)

            # 2. 性别与年龄 (4-6位)
            gender_widget = self.table.cellWidget(row, 2)
            gender = gender_widget.currentText() if gender_widget else "其他"
            gender_code = 'M' if gender == '男' else ('F' if gender == '女' else 'G')
            
            age_item = self.table.item(row, 3)
            age_text = age_item.text() if age_item else "0"
            age = int(re.sub(r'\D', '', age_text)) if any(c.isdigit() for c in age_text) else 0
            part2 = f"{gender_code}{min(age, 99):02d}"

            # 3. 日期 (7-9位)
            today = datetime.datetime.now()
            part3 = f"{str(today.year)[-2:]}{self.get_month_code(today.month)}"

            # 4. 前缀与版本 (10-12位)
            prefix = mol_text[0] if mol_text else 'K'
            part4 = f"{PREFIX_MAP.get(prefix, '0')}V1"

            return f"{part1}{part2}{part3}{part4}"
        except Exception:
            return "计算中..."

    # --- 交互功能 ---

    def add_new_row(self, data=None):
        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)
        
        # 删除按钮
        del_btn = QPushButton("删除")
        del_btn.setStyleSheet("color: #e74c3c; border: none; background: transparent; font-weight: bold;")
        # 注意：此处使用 row_id 替代 row 索引，防止删除行后索引错乱
        del_btn.clicked.connect(self.handle_delete_action)
        self.table.setCellWidget(row_pos, 0, del_btn)

        # [cite_start]性别下拉框[span_5](end_span)
        gender_combo = QComboBox()
        gender_combo.addItems(["请选择", "男", "女", "其他"])
        gender_combo.currentTextChanged.connect(lambda: self.update_row_code(self.table.currentRow()))
        self.table.setCellWidget(row_pos, 2, gender_combo)

        if data:
            # 导入模式
            fields = [1, 3, 4, 5, 6, 7] # 姓名, 年龄, 分子号, 病案号, 诊断, 备注
            for i, field_idx in enumerate(fields):
                self.table.setItem(row_pos, field_idx, QTableWidgetItem(str(data[i])))
            if len(data) > 6: gender_combo.setCurrentText(data[6])
        else:
            # 手动添加模式：分子号自动递增
            next_mol = self.get_next_molecular_number()
            self.table.setItem(row_pos, 4, QTableWidgetItem(next_mol))
            for i in [1, 3, 5, 6, 7]:
                self.table.setItem(row_pos, i, QTableWidgetItem(""))

        self.update_row_code(row_pos)
        self.update_stats()

    def handle_delete_action(self):
        button = self.sender()
        if button:
            index = self.table.indexAt(button.pos())
            if index.isValid():
                self.table.removeRow(index.row())
                self.update_stats()

    def update_row_code(self, row):
        if row < 0: return
        code = self.calculate_row_code(row)
        item = QTableWidgetItem(code)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled) # Code不可编辑
        self.table.setItem(row, 8, item)

    def handle_cell_changed(self, row, column):
        if column in [3, 4]: # 年龄或分子号变动
            self.update_row_code(row)
        self.update_stats()

    def apply_prefix_to_all(self):
        new_prefix = self.prefix_combo.currentText()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)
            if item:
                old_text = item.text()
                match = re.search(r'(\d{4})$', old_text)
                num_part = match.group(1) if match else f"{row+1:04d}"
                item.setText(f"{new_prefix}{num_part}")
        QMessageBox.information(self, "完成", f"已将所有分子号前缀统一更新为: {new_prefix}")

    def update_stats(self):
        [cite_start]"""更新底部统计数据 [cite: 161-163]"""
        total = self.table.rowCount()
        males = 0
        females = 0
        for r in range(total):
            w = self.table.cellWidget(r, 2)
            if w and w.currentText() == "男": males += 1
            elif w and w.currentText() == "女": females += 1
        
        self.total_label.setText(f"总记录数: {total}")
        self.male_label.setText(f"男性: {males}")
        self.female_label.setText(f"女性: {females}")

    def export_to_excel(self):
        [cite_start]"""导出数据到Excel [cite: 157-159]"""
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "提示", "没有可导出的数据")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "导出Excel", f"临床数据_{datetime.datetime.now().strftime('%Y%02m%02d')}.xlsx", "Excel Files (*.xlsx)")
        if path:
            rows_data = []
            headers = ["姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code"]
            for r in range(self.table.rowCount()):
                row = []
                row.append(self.table.item(r, 1).text() if self.table.item(r, 1) else "")
                row.append(self.table.cellWidget(r, 2).currentText())
                row.append(self.table.item(r, 3).text() if self.table.item(r, 3) else "")
                row.append(self.table.item(r, 4).text() if self.table.item(r, 4) else "")
                row.append(self.table.item(r, 5).text() if self.table.item(r, 5) else "")
                row.append(self.table.item(r, 6).text() if self.table.item(r, 6) else "")
                row.append(self.table.item(r, 7).text() if self.table.item(r, 7) else "")
                row.append(self.table.item(r, 8).text() if self.table.item(r, 8) else "")
                rows_data.append(row)
            
            df = pd.DataFrame(rows_data, columns=headers)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", f"文件已保存至:\n{path}")

    def import_from_excel(self):
        [cite_start]"""从Excel导入数据 [cite: 116-137]"""
        path, _ = QFileDialog.getOpenFileName(self, "选择Excel文件", "", "Excel Files (*.xlsx *.xls)")
        if path:
            try:
                df = pd.read_excel(path).fillna("")
                for _, row in df.iterrows():
                    # 匹配逻辑：姓名, 性别(转义), 年龄, 分子号, 病案号, 诊断, 备注
                    g_raw = str(row.iloc[1])
                    gender = "男" if g_raw in ['男', 'M', 'Male'] else ("女" if g_raw in ['女', 'F', 'Female'] else "其他")
                    # 提取纯数字年龄
                    a_raw = str(row.iloc[2])
                    age = re.sub(r'\D', '', a_raw) if a_raw else "0"
                    
                    data_list = [row.iloc[0], age, row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6], gender]
                    self.add_new_row(data_list)
                QMessageBox.information(self, "成功", f"成功导入 {len(df)} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件失败: {str(e)}")

    def reset_data(self):
        if QMessageBox.question(self, "确认", "这将清空当前表格所有内容，是否继续？") == QMessageBox.StandardButton.Yes:
            self.table.setRowCount(0)
            self.add_new_row()
            self.update_stats()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局字体
    app.setFont(QFont("Microsoft YaHei", 9))
    window = ClinicalDataApp()
    window.show()
    sys.exit(app.exec())
