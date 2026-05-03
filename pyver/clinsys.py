import sys
import re
import datetime
import pandas as pd
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QLabel, QHeaderView, QFileDialog, QMessageBox, 
                             QFrame, QAbstractItemView, QTabWidget, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 基础配置
BASE32_CHARS = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

class ClinicalUltimateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("临床数据管理系统 v4.5 260503")
        self.resize(1500, 900)
        self.db_path = ""
        self.total_df = pd.DataFrame() 
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        # 1. 顶部状态栏
        top_bar = QHBoxLayout()
        self.db_status_label = QLabel("🔴 未连接总库")
        self.db_status_label.setStyleSheet("font-weight: bold; color: #c0392b; font-size: 14px;")
        
        load_db_btn = QPushButton("连接数据库")
        load_db_btn.clicked.connect(self.connect_database)
        
        limit_hint = QLabel("⚠️分子号最大支持32767，超过请手动调整前缀")
        limit_hint.setStyleSheet("color: #7f8c8d; font-style: italic; margin-left: 20px;")
        
        top_bar.addWidget(self.db_status_label)
        top_bar.addWidget(load_db_btn)
        top_bar.addWidget(limit_hint)
        top_bar.addStretch()
        self.layout.addLayout(top_bar)

        # 2. 主标签页
        self.tabs = QTabWidget()
        self.tab_stock_in = QWidget()
        self.tab_stock_out = QWidget()
        self.tabs.addTab(self.tab_stock_in, "数据录入")
        self.tabs.addTab(self.tab_stock_out, "数据检索")
        self.layout.addWidget(self.tabs)

        self.init_stock_in_ui()
        self.init_stock_out_ui()

    def init_stock_in_ui(self):
        layout = QVBoxLayout(self.tab_stock_in)

        # A. 前缀管理
        tool_frame = QHBoxLayout()
        tool_frame.addWidget(QLabel("分子号前缀:"))
        self.prefix_combo = QComboBox()
        letters = [chr(i) for i in range(65, 91)]
        main_p = ["K", "L"]
        other_p = sorted([l for l in letters if l not in main_p])
        self.prefix_combo.addItems(main_p + other_p)
        tool_frame.addWidget(self.prefix_combo)
        
        apply_prefix_btn = QPushButton("更新分子号前缀")
        apply_prefix_btn.clicked.connect(self.apply_prefix_to_table)
        tool_frame.addWidget(apply_prefix_btn)
        
        self.import_local_btn = QPushButton("批量输入")
        self.import_local_btn.clicked.connect(self.import_to_entry_table)
        tool_frame.addWidget(self.import_local_btn)

        self.reset_btn = QPushButton("重置列表")
        self.reset_btn.clicked.connect(self.reset_entry_table)
        tool_frame.addWidget(self.reset_btn)
        tool_frame.addStretch()
        layout.addLayout(tool_frame)

        # B. 按钮区
        action_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("+ 新增行")
        self.export_label_btn = QPushButton("打印标签")
        self.export_label_btn.setStyleSheet("background-color: #f39c12; color: white;")
        self.save_to_db_btn = QPushButton("保存数据")
        self.save_to_db_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 20px;")
        
        action_layout.addWidget(self.add_row_btn)
        action_layout.addWidget(self.export_label_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.save_to_db_btn)
        layout.addLayout(action_layout)

        # C. 录入表
        self.entry_table = QTableWidget()
        self.entry_table.setColumnCount(9)
        self.entry_table.setHorizontalHeaderLabels(["操作", "姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code"])
        self.entry_table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.entry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.entry_table)

        # D. 统计面板
        stats_layout = QHBoxLayout()
        self.stat_total = QLabel("当前待入库: 0")
        self.stat_male = QLabel("男: 0")
        self.stat_female = QLabel("女: 0")
        for lbl in [self.stat_total, self.stat_male, self.stat_female]:
            lbl.setStyleSheet("font-weight: bold; color: #2c3e50;")
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        self.add_row_btn.clicked.connect(self.add_entry_row)
        self.export_label_btn.clicked.connect(self.export_for_labels)
        self.save_to_db_btn.clicked.connect(self.write_to_database)
        self.entry_table.cellChanged.connect(self.handle_entry_cell_changed)

    def init_stock_out_ui(self):
        layout = QVBoxLayout(self.tab_stock_out)
        
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("扫码/关键词:"))
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("在此扫码或输入搜索关键词...")
        self.scan_input.setStyleSheet("background-color: #fff9db;")
        self.scan_input.returnPressed.connect(self.handle_barcode_scan)
        tool_layout.addWidget(self.scan_input)
        
        self.search_col_combo = QComboBox()
        self.search_col_combo.addItems(["姓名", "分子号", "病案号", "诊断", "Code"])
        tool_layout.addWidget(self.search_col_combo)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_database)
        tool_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.out_table.setRowCount(0))
        export_out_btn = QPushButton("保存结果")
        export_out_btn.clicked.connect(self.export_out_results)
        
        tool_layout.addStretch()
        tool_layout.addWidget(clear_btn)
        tool_layout.addWidget(export_out_btn)
        layout.addLayout(tool_layout)

        self.out_table = QTableWidget()
        self.out_table.setColumnCount(10)
        self.out_table.setHorizontalHeaderLabels(["姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code", "采集时间", "日期"])
        self.out_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.out_table)

    # --- 核心逻辑 ---

    def decode_collection_time(self, code):
        try:
            if len(code) < 9: return ""
            year = "20" + code[6:8]
            m_char = code[8]
            month = m_char.zfill(2) if m_char.isdigit() else str(ord(m_char) - 55)
            return f"{year}{month.zfill(2)}"
        except: return ""

    def calculate_row_code(self, row):
        try:
            mol_item = self.entry_table.item(row, 4)
            mol_text = mol_item.text() if mol_item else ""
            match = re.search(r'\d+$', mol_text)
            num = int(match.group()) if match else 0
            p1 = self.to_base32(num)
            
            gw = self.entry_table.cellWidget(row, 2)
            gc = 'M' if gw.currentText() == '男' else ('F' if gw.currentText() == '女' else 'G')
            age_t = self.entry_table.item(row, 3).text() if self.entry_table.item(row, 3) else "0"
            p2 = f"{gc}{min(int(age_t) if age_t.isdigit() else 0, 99):02d}"
            
            td = datetime.datetime.now()
            p3 = f"{str(td.year)[-2:]}{self.get_month_code(td.month)}"
            
            prefix_char = mol_text[0].upper() if (mol_text and mol_text[0].isalpha()) else "K"
            return f"{p1}{p2}{p3}{prefix_char}V1"
        except: return ""

    def connect_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "连接总数据库", "", "Excel Files (*.xlsx)")
        if path:
            try:
                self.db_path = path
                self.total_df = pd.read_excel(path).fillna("")
                self.db_status_label.setText(f"🟢 总库: {os.path.basename(path)}")
                self.db_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def handle_row_delete(self):
        btn = self.sender()
        if btn:
            idx = self.entry_table.indexAt(btn.pos()).row()
            self.entry_table.removeRow(idx)
            self.update_stats()

    def handle_entry_cell_changed(self, row, col):
        if col == 3: # 年龄去“岁”
            item = self.entry_table.item(row, col)
            if item:
                val = re.sub(r'\D', '', item.text())
                if val != item.text():
                    self.entry_table.blockSignals(True)
                    item.setText(val)
                    self.entry_table.blockSignals(False)
        
        if col == 5: # 病案号查重（非0）
            item = self.entry_table.item(row, col)
            if item and not self.total_df.empty:
                cid = item.text().strip()
                if cid and cid != "0":
                    match = self.total_df[self.total_df['病案号'].astype(str) == cid]
                    if not match.empty:
                        old_mol = str(match.iloc[0]['分子号'])
                        self.entry_table.blockSignals(True)
                        self.entry_table.setItem(row, 4, QTableWidgetItem(old_mol))
                        self.entry_table.blockSignals(False)
                        QMessageBox.information(self, "随访识别", f"分子号自动同步为: {old_mol}")

        if col in [2, 3, 4]: 
            self.entry_table.setItem(row, 8, QTableWidgetItem(self.calculate_row_code(row)))
        self.update_stats()

    def update_stats(self):
        total = self.entry_table.rowCount()
        m, f = 0, 0
        for r in range(total):
            gw = self.entry_table.cellWidget(r, 2)
            if gw and gw.currentText() == "男": m += 1
            elif gw and gw.currentText() == "女": f += 1
        self.stat_total.setText(f"待入库: {total}"); self.stat_male.setText(f"男: {m}"); self.stat_female.setText(f"女: {f}")

    def write_to_database(self):
        if not self.db_path: 
            QMessageBox.warning(self, "提示", "请先连接总库")
            return
        new_data = []
        today = datetime.datetime.now().strftime('%Y%m%d')
        for r in range(self.entry_table.rowCount()):
            name = self.entry_table.item(r, 1).text() if self.entry_table.item(r, 1) else ""
            if not name: continue
            new_data.append({
                "姓名": name, "性别": self.entry_table.cellWidget(r, 2).currentText(),
                "年龄": self.entry_table.item(r, 3).text(), "分子号": self.entry_table.item(r, 4).text(),
                "病案号": self.entry_table.item(r, 5).text(), "诊断": self.entry_table.item(r, 6).text(),
                "诊断备注": self.entry_table.item(r, 7).text(), "Code": self.entry_table.item(r, 8).text(),
                "日期": today
            })
        if new_data:
            try:
                self.total_df = pd.concat([self.total_df, pd.DataFrame(new_data)], ignore_index=True)
                self.total_df.to_excel(self.db_path, index=False)
                QMessageBox.information(self, "成功", "总库已同步。")
                self.entry_table.setRowCount(0); self.add_entry_row()
            except Exception as e: QMessageBox.critical(self, "写入失败", str(e))

    def display_out(self, df, clear=True):
        if clear: self.out_table.setRowCount(0)
        cols = ["姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code"]
        for _, row in df.iterrows():
            idx = self.out_table.rowCount()
            self.out_table.insertRow(idx)
            for i, c in enumerate(cols): self.out_table.setItem(idx, i, QTableWidgetItem(str(row.get(c, ""))))
            code_v = str(row.get("Code", ""))
            self.out_table.setItem(idx, 8, QTableWidgetItem(self.decode_collection_time(code_v)))
            self.out_table.setItem(idx, 9, QTableWidgetItem(str(row.get("日期", ""))))

    def add_entry_row(self, data=None):
        r = self.entry_table.rowCount()
        self.entry_table.insertRow(r)
        del_btn = QPushButton("删除")
        del_btn.setStyleSheet("color: #e74c3c; border: none;")
        del_btn.clicked.connect(self.handle_row_delete)
        self.entry_table.setCellWidget(r, 0, del_btn)
        g_combo = QComboBox(); g_combo.addItems(["请选择", "男", "女", "其他"])
        g_combo.currentTextChanged.connect(lambda: self.entry_table.setItem(self.entry_table.indexAt(g_combo.pos()).row(), 8, QTableWidgetItem(self.calculate_row_code(self.entry_table.indexAt(g_combo.pos()).row()))))
        self.entry_table.setCellWidget(r, 2, g_combo)
        if data:
            for i, f_idx in enumerate([1, 3, 4, 5, 6, 7]): self.entry_table.setItem(r, f_idx, QTableWidgetItem(str(data[i])))
            g_combo.setCurrentText(data[6])
        else:
            self.entry_table.setItem(r, 4, QTableWidgetItem(self.get_next_molecular_number()))
            for i in [1, 3, 5, 6, 7]: self.entry_table.setItem(r, i, QTableWidgetItem(""))
        self.update_stats()

    def get_next_molecular_number(self):
        prefix = self.prefix_combo.currentText()
        max_n = 0
        for r in range(self.entry_table.rowCount()):
            item = self.entry_table.item(r, 4)
            if item:
                m = re.search(r'(\d+)$', item.text())
                if m: max_n = max(max_n, int(m.group(1)))
        return f"{prefix}{max_n + 1:05d}"

    def apply_prefix_to_table(self):
        prefix = self.prefix_combo.currentText()
        for r in range(self.entry_table.rowCount()):
            item = self.entry_table.item(r, 4)
            if item:
                m = re.search(r'(\d+)$', item.text())
                num = m.group(1).rjust(5, '0') if m else f"{r+1:05d}"
                item.setText(f"{prefix}{num}")

    def reset_entry_table(self):
        if QMessageBox.question(self, "确认", "重置录入列表？") == QMessageBox.StandardButton.Yes:
            self.entry_table.setRowCount(0); self.add_entry_row(); self.update_stats()

    def export_for_labels(self):
        if self.entry_table.rowCount() == 0: return
        today = datetime.datetime.now().strftime('%Y%m%d')
        path, _ = QFileDialog.getSaveFileName(self, "导出标签", f"标签_{today}.xlsx", "Excel Files (*.xlsx)")
        if path:
            data = []
            h = ["姓名", "性别", "年龄", "分子号", "病案号", "诊断", "备注", "Code", "Len", "姓名2", "分子号2", "日期"]
            for r in range(self.entry_table.rowCount()):
                name, mol, code = self.entry_table.item(r,1).text(), self.entry_table.item(r,4).text(), self.entry_table.item(r,8).text()
                data.append([name, self.entry_table.cellWidget(r,2).currentText(), self.entry_table.item(r,3).text(), mol, self.entry_table.item(r,5).text(), self.entry_table.item(r,6).text(), self.entry_table.item(r,7).text(), code, len(code), name, mol, today])
            pd.DataFrame(data, columns=h).to_excel(path, index=False)

    def import_to_entry_table(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入待入库数据", "", "Excel Files (*.xlsx)")
        if path:
            df = pd.read_excel(path).fillna("")
            for _, r in df.iterrows():
                g = "男" if str(r.iloc[1]) in ['男', 'M'] else ("女" if str(r.iloc[1]) in ['女', 'F'] else "其他")
                self.add_entry_row([r.iloc[0], re.sub(r'\D','',str(r.iloc[2])), r.iloc[3], r.iloc[4], r.iloc[5], r.iloc[6], g])

    def search_database(self):
        col, kw = self.search_col_combo.currentText(), self.scan_input.text().strip()
        if not self.total_df.empty and kw:
            res = self.total_df[self.total_df[col].astype(str).str.contains(kw, case=False)]
            self.display_out(res, True)

    def handle_barcode_scan(self):
        code = self.scan_input.text().strip()
        self.scan_input.clear()
        if not self.total_df.empty and code:
            match = self.total_df[self.total_df['Code'].astype(str) == code]
            if not match.empty: self.display_out(match, False)

    def export_out_results(self):
        if self.out_table.rowCount() == 0: return
        path, _ = QFileDialog.getSaveFileName(self, "保存检索结果", "结果导出.xlsx", "Excel Files (*.xlsx)")
        if path:
            data = []
            h = ["姓名", "性别", "年龄", "分子号", "病案号", "诊断", "诊断备注", "Code", "采集时间", "日期"]
            for r in range(self.out_table.rowCount()): data.append([self.out_table.item(r, c).text() for c in range(10)])
            pd.DataFrame(data, columns=h).to_excel(path, index=False)

    def to_base32(self, n):
        if n == 0: return '000'
        res = ''
        while n > 0:
            res = BASE32_CHARS[n % 32] + res
            n //= 32
        return res.rjust(3, '0')

    def get_month_code(self, m):
        return str(m) if m < 10 else chr(55+m)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    win = ClinicalUltimateApp()
    win.show()
    sys.exit(app.exec())

# python -m nuitka --standalone --show-progress --enable-plugin=pyqt6 --windows-disable-console C:\Users\Jerry\Downloads\clinsys.py    