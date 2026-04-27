import sys
import datetime
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QLabel, QHeaderView, QFileDialog, QMessageBox, 
                             QFrame, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

# 基础配置与逻辑映射
BASE32_CHARS = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
PREFIX_MAP = {'K': '0', 'L': '1', 'U': '2'}

class ClinicalDataApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("临床数据录入系统")
        self.resize(1200, 800)
        self.setup_ui()
        self.add_new_row() # 默认添加一行

    def setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # 头部：标题与主按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("临床数据录入系统")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        
        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("添加行")
        self.import_btn = QPushButton("导入Excel")
        self.export_btn = QPushButton("导出Excel")
        self.reset_btn = QPushButton("重置")
        
        # 样式美化
        self.add_row_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px;")
        self.export_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        self.import_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        self.reset_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px;")

        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.reset_btn)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(btn_layout)
        self.main_layout.addLayout(header_layout)

        # 前缀设置区
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

        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["操作", "姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table)

        # 统计栏
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("总记录数: 0")
        self.male_label = QLabel("男性: 0")
        self.female_label = QLabel("女性: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.male_label)
        stats_layout.addWidget(self.female_label)
        self.main_layout.addLayout(stats_layout)

        # 信号连接
        self.add_row_btn.clicked.connect(self.add_new_row)
        self.export_btn.clicked.connect(self.export_to_excel)
        self.import_btn.clicked.connect(self.import_from_excel)
        self.reset_btn.clicked.connect(self.reset_data)
        self.apply_prefix_btn.clicked.connect(self.apply_prefix_to_all)
        self.table.cellChanged.connect(self.handle_cell_changed)

    # --- 核心逻辑方法 ---

    def to_base32(self, num):
        if num == 0: return '000'
        res = ''
        n = num
        while n > 0:
            res = BASE32_CHARS[n % 32] + res
            n //= 32
        return res.rjust(3, '0')

    def get_month_code(self, month):
        if 1 <= month <= 9: return str(month)
        codes = {10: 'A', 11: 'B', 12: 'C'}
        return codes.get(month, '0')

    def calculate_row_code(self, row):
        try:
            # 1. 分子号Base32
            mol_text = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            import re
            match = re.search(r'\d{4}$', mol_text)
            num = int(match.group()) if match else 0
            part1 = self.to_base32(num)

            # 2. 性别与年龄
            gender_widget = self.table.cellWidget(row, 2)
            gender = gender_widget.currentText() if gender_widget else "其他"
            gender_code = 'M' if gender == '男' else ('F' if gender == '女' else 'G')
            
            age_text = self.table.item(row, 3).text() if self.table.item(row, 3) else "0"
            age = int(age_text) if age_text.isdigit() else 0
            part2 = f"{gender_code}{min(age, 99):02d}"

            # 3. 日期
            today = datetime.datetime.now()
            part3 = f"{str(today.year)[-2:]}{self.get_month_code(today.month)}"

            # 4. 扩展位
            prefix = mol_text[0] if mol_text else 'K'
            part4 = f"{PREFIX_MAP.get(prefix, '0')}V1"

            return f"{part1}{part2}{part3}{part4}"
        except Exception:
            return "待计算"

    # --- 槽函数 ---

    def add_new_row(self, data=None):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        # 操作列：删除按钮
        del_btn = QPushButton("删除")
        del_btn.setStyleSheet("color: #e74c3c;")
        del_btn.clicked.connect(lambda: self.delete_row(row_position))
        self.table.setCellWidget(row_position, 0, del_btn)

        # 性别列：下拉框
        gender_combo = QComboBox()
        gender_combo.addItems(["请选择", "男", "女", "其他"])
        gender_combo.currentTextChanged.connect(lambda: self.update_row_code(row_position))
        self.table.setCellWidget(row_position, 2, gender_combo)

        # 填充数据 (如果有导入数据)
        fields = [1, 3, 4, 5, 6, 7] # 姓名, 年龄, 分子号, 病案号, 诊断, 备注
        if data:
            for i, field_idx in enumerate(fields):
                val = str(data[i]) if i < len(data) else ""
                self.table.setItem(row_position, field_idx, QTableWidgetItem(val))
            if len(data) > 6: # 性别在导入数据的特定位置
                gender_combo.setCurrentText(data[6])
        else:
            # 默认分子号逻辑
            prefix = self.prefix_combo.currentText()
            mol_num = f"{prefix}{row_position + 1:04d}"
            self.table.setItem(row_position, 4, QTableWidgetItem(mol_num))
            for i in [1, 3, 5, 6, 7]:
                self.table.setItem(row_position, i, QTableWidgetItem(""))

        self.update_row_code(row_position)
        self.update_stats()

    def update_row_code(self, row):
        code = self.calculate_row_code(row)
        self.table.setItem(row, 8, QTableWidgetItem(code))

    def handle_cell_changed(self, row, column):
        if column in [2, 3, 4]: # 影响Code的列
            self.update_row_code(row)
        self.update_stats()

    def delete_row(self, row):
        self.table.removeRow(row)
        self.update_stats()

    def apply_prefix_to_all(self):
        new_prefix = self.prefix_combo.currentText()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)
            if item:
                import re
                match = re.search(r'\d{4}$', item.text())
                num_part = match.group() if match else f"{row+1:04d}"
                item.setText(f"{new_prefix}{num_part}")
        QMessageBox.information(self, "提示", f"已统一前缀为 {new_prefix}")

    def update_stats(self):
        total = self.table.rowCount()
        males = 0
        females = 0
        for r in range(total):
            w = self.table.cellWidget(r, 2)
            if w and w.currentText() == "男": males += 1
            if w and w.currentText() == "女": females += 1
        
        self.total_label.setText(f"总记录数: {total}")
        self.male_label.setText(f"男性: {males}")
        self.female_label.setText(f"女性: {females}")

    def export_to_excel(self):
        if self.table.rowCount() == 0: return
        
        path, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "Excel Files (*.xlsx)")
        if path:
            data = []
            for r in range(self.table.rowCount()):
                row_data = {}
                row_data['姓名'] = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                row_data['性别'] = self.table.cellWidget(r, 2).currentText()
                row_data['年龄'] = self.table.item(r, 3).text() if self.table.item(r, 3) else ""
                row_data['分子号'] = self.table.item(r, 4).text() if self.table.item(r, 4) else ""
                row_data['Code'] = self.table.item(r, 8).text() if self.table.item(r, 8) else ""
                data.append(row_data)
            
            df = pd.DataFrame(data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", "数据已成功导出！")

    def import_from_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "Excel Files (*.xlsx *.xls)")
        if path:
            df = pd.read_excel(path)
            # 简单演示：按列顺序读取
            for _, row in df.iterrows():
                # 转换性别格式
                g = str(row.iloc[1])
                gender = "男" if g in ['男', 'M'] else ("女" if g in ['女', 'F'] else "其他")
                # 姓名, 年龄, 分子号, 病案号, 诊断, 备注, 性别
                data_list = [row.iloc[0], row.iloc[2], row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6], gender]
                self.add_new_row(data_list)

    def reset_data(self):
        if QMessageBox.question(self, "重置", "确定要清空所有数据吗？") == QMessageBox.StandardButton.Yes:
            self.table.setRowCount(0)
            self.add_new_row()
            self.update_stats()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClinicalDataApp()
    window.show()
    sys.exit(app.exec())
