#include "ClinicalApp.h"

#include <QAbstractItemView>
#include <QComboBox>
#include <QDate>
#include <QFileDialog>
#include <QFileInfo>
#include <QHeaderView>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QRegularExpression>
#include <QSignalBlocker>
#include <QTabWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>

namespace {
const QStringList kDbHeaders = {
    QStringLiteral("姓名"),
    QStringLiteral("性别"),
    QStringLiteral("年龄"),
    QStringLiteral("分子号"),
    QStringLiteral("病案号"),
    QStringLiteral("诊断"),
    QStringLiteral("诊断备注"),
    QStringLiteral("Code"),
    QStringLiteral("日期")
};

const QStringList kOutHeaders = {
    QStringLiteral("姓名"),
    QStringLiteral("性别"),
    QStringLiteral("年龄"),
    QStringLiteral("分子号"),
    QStringLiteral("病案号"),
    QStringLiteral("诊断"),
    QStringLiteral("诊断备注"),
    QStringLiteral("Code"),
    QStringLiteral("采集时间"),
    QStringLiteral("日期")
};

const QString kBase32Chars = QStringLiteral("0123456789ABCDEFGHJKMNPQRSTVWXYZ");
}

ClinicalApp::ClinicalApp(QWidget *parent)
    : QMainWindow(parent)
{
    setWindowTitle(QStringLiteral("临床数据管理系统 v4.5 260503 - C++"));
    resize(1500, 900);
    setupUi();
}

void ClinicalApp::setupUi()
{
    auto *central = new QWidget(this);
    setCentralWidget(central);

    auto *mainLayout = new QVBoxLayout(central);
    auto *topBar = new QHBoxLayout();

    m_dbStatusLabel = new QLabel(QStringLiteral("未连接总库"), this);
    m_dbStatusLabel->setStyleSheet(QStringLiteral("font-weight: bold; color: #c0392b; font-size: 14px;"));

    auto *loadDbButton = new QPushButton(QStringLiteral("连接数据库"), this);
    connect(loadDbButton, &QPushButton::clicked, this, &ClinicalApp::connectDatabase);

    auto *limitHint = new QLabel(QStringLiteral("分子号最大支持32767，超过请手动调整前缀"), this);
    limitHint->setStyleSheet(QStringLiteral("color: #7f8c8d; font-style: italic; margin-left: 20px;"));

    topBar->addWidget(m_dbStatusLabel);
    topBar->addWidget(loadDbButton);
    topBar->addWidget(limitHint);
    topBar->addStretch();
    mainLayout->addLayout(topBar);

    auto *tabs = new QTabWidget(this);
    auto *stockInTab = new QWidget(tabs);
    auto *stockOutTab = new QWidget(tabs);
    tabs->addTab(stockInTab, QStringLiteral("数据录入"));
    tabs->addTab(stockOutTab, QStringLiteral("数据检索"));
    mainLayout->addWidget(tabs);

    initStockInUi(stockInTab);
    initStockOutUi(stockOutTab);
    addEntryRow();
}

void ClinicalApp::initStockInUi(QWidget *tab)
{
    auto *layout = new QVBoxLayout(tab);

    auto *toolFrame = new QHBoxLayout();
    toolFrame->addWidget(new QLabel(QStringLiteral("分子号前缀:"), tab));
    m_prefixCombo = new QComboBox(tab);
    m_prefixCombo->addItems(QStringList{QStringLiteral("K"), QStringLiteral("L")});
    for (QChar ch = 'A'; ch <= 'Z'; ch = QChar(ch.unicode() + 1)) {
        const QString letter(ch);
        if (letter != QStringLiteral("K") && letter != QStringLiteral("L")) {
            m_prefixCombo->addItem(letter);
        }
    }
    toolFrame->addWidget(m_prefixCombo);

    auto *applyPrefixButton = new QPushButton(QStringLiteral("更新分子号前缀"), tab);
    connect(applyPrefixButton, &QPushButton::clicked, this, &ClinicalApp::applyPrefixToTable);
    toolFrame->addWidget(applyPrefixButton);

    auto *importButton = new QPushButton(QStringLiteral("批量输入"), tab);
    connect(importButton, &QPushButton::clicked, this, &ClinicalApp::importToEntryTable);
    toolFrame->addWidget(importButton);

    auto *resetButton = new QPushButton(QStringLiteral("重置列表"), tab);
    connect(resetButton, &QPushButton::clicked, this, &ClinicalApp::resetEntryTable);
    toolFrame->addWidget(resetButton);
    toolFrame->addStretch();
    layout->addLayout(toolFrame);

    auto *actionLayout = new QHBoxLayout();
    auto *addRowButton = new QPushButton(QStringLiteral("+ 新增行"), tab);
    connect(addRowButton, &QPushButton::clicked, this, &ClinicalApp::addEntryRow);
    auto *exportLabelButton = new QPushButton(QStringLiteral("打印标签"), tab);
    exportLabelButton->setStyleSheet(QStringLiteral("background-color: #f39c12; color: white;"));
    connect(exportLabelButton, &QPushButton::clicked, this, &ClinicalApp::exportForLabels);
    auto *saveButton = new QPushButton(QStringLiteral("保存数据"), tab);
    saveButton->setStyleSheet(QStringLiteral("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 20px;"));
    connect(saveButton, &QPushButton::clicked, this, &ClinicalApp::writeToDatabase);

    actionLayout->addWidget(addRowButton);
    actionLayout->addWidget(exportLabelButton);
    actionLayout->addStretch();
    actionLayout->addWidget(saveButton);
    layout->addLayout(actionLayout);

    m_entryTable = new QTableWidget(tab);
    m_entryTable->setColumnCount(9);
    m_entryTable->setHorizontalHeaderLabels({
        QStringLiteral("操作"),
        QStringLiteral("姓名"),
        QStringLiteral("性别"),
        QStringLiteral("年龄"),
        QStringLiteral("分子号"),
        QStringLiteral("病案号"),
        QStringLiteral("诊断"),
        QStringLiteral("诊断备注"),
        QStringLiteral("Code")
    });
    m_entryTable->setEditTriggers(QAbstractItemView::AllEditTriggers);
    m_entryTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    connect(m_entryTable, &QTableWidget::cellChanged, this, &ClinicalApp::handleEntryCellChanged);
    layout->addWidget(m_entryTable);

    auto *statsLayout = new QHBoxLayout();
    m_statTotal = new QLabel(QStringLiteral("当前待入库 0"), tab);
    m_statMale = new QLabel(QStringLiteral("男 0"), tab);
    m_statFemale = new QLabel(QStringLiteral("女 0"), tab);
    for (QLabel *label : {m_statTotal, m_statMale, m_statFemale}) {
        label->setStyleSheet(QStringLiteral("font-weight: bold; color: #2c3e50;"));
        statsLayout->addWidget(label);
    }
    statsLayout->addStretch();
    layout->addLayout(statsLayout);
}

void ClinicalApp::initStockOutUi(QWidget *tab)
{
    auto *layout = new QVBoxLayout(tab);
    auto *toolLayout = new QHBoxLayout();

    toolLayout->addWidget(new QLabel(QStringLiteral("扫码/关键词:"), tab));
    m_scanInput = new QLineEdit(tab);
    m_scanInput->setPlaceholderText(QStringLiteral("在此扫码或输入搜索关键词..."));
    m_scanInput->setStyleSheet(QStringLiteral("background-color: #fff9db;"));
    connect(m_scanInput, &QLineEdit::returnPressed, this, &ClinicalApp::handleBarcodeScan);
    toolLayout->addWidget(m_scanInput);

    m_searchColumnCombo = new QComboBox(tab);
    m_searchColumnCombo->addItems({
        QStringLiteral("姓名"),
        QStringLiteral("分子号"),
        QStringLiteral("病案号"),
        QStringLiteral("诊断"),
        QStringLiteral("Code")
    });
    toolLayout->addWidget(m_searchColumnCombo);

    auto *searchButton = new QPushButton(QStringLiteral("搜索"), tab);
    connect(searchButton, &QPushButton::clicked, this, &ClinicalApp::searchDatabase);
    toolLayout->addWidget(searchButton);

    auto *clearButton = new QPushButton(QStringLiteral("清空"), tab);
    connect(clearButton, &QPushButton::clicked, this, [this]() { m_outTable->setRowCount(0); });
    auto *exportButton = new QPushButton(QStringLiteral("保存结果"), tab);
    connect(exportButton, &QPushButton::clicked, this, &ClinicalApp::exportOutResults);

    toolLayout->addStretch();
    toolLayout->addWidget(clearButton);
    toolLayout->addWidget(exportButton);
    layout->addLayout(toolLayout);

    m_outTable = new QTableWidget(tab);
    m_outTable->setColumnCount(10);
    m_outTable->setHorizontalHeaderLabels(kOutHeaders);
    m_outTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    layout->addWidget(m_outTable);
}

void ClinicalApp::connectDatabase()
{
    const QString path = QFileDialog::getOpenFileName(
        this,
        QStringLiteral("连接总数据库"),
        QString(),
        QStringLiteral("CSV Files (*.csv);;All Files (*)"));
    if (path.isEmpty()) {
        return;
    }

    QString error;
    CsvTable table;
    if (!table.load(path, &error)) {
        QMessageBox::critical(this, QStringLiteral("错误"), error);
        return;
    }

    m_dbPath = path;
    m_totalTable = table;
    ensureDatabaseHeaders();
    m_dbStatusLabel->setText(QStringLiteral("总库: %1").arg(QFileInfo(path).fileName()));
    m_dbStatusLabel->setStyleSheet(QStringLiteral("color: #27ae60; font-weight: bold;"));
}

void ClinicalApp::addEntryRow()
{
    addEntryRowFromData({});
}

void ClinicalApp::addEntryRowFromData(const QStringList &data)
{
    const int row = m_entryTable->rowCount();
    m_entryTable->insertRow(row);

    auto *deleteButton = new QPushButton(QStringLiteral("删除"), m_entryTable);
    deleteButton->setStyleSheet(QStringLiteral("color: #e74c3c; border: none;"));
    connect(deleteButton, &QPushButton::clicked, this, &ClinicalApp::deleteEntryRow);
    m_entryTable->setCellWidget(row, 0, deleteButton);

    auto *genderCombo = new QComboBox(m_entryTable);
    genderCombo->addItems({
        QStringLiteral("请选择"),
        QStringLiteral("男"),
        QStringLiteral("女"),
        QStringLiteral("其他")
    });
    connect(genderCombo, &QComboBox::currentTextChanged, this, [this, genderCombo]() {
        const int row = m_entryTable->indexAt(genderCombo->pos()).row();
        if (row >= 0) {
            refreshCodeForRow(row);
            updateStats();
        }
    });
    m_entryTable->setCellWidget(row, 2, genderCombo);

    if (data.size() >= 7) {
        setEntryText(row, 1, data[0]);
        setEntryText(row, 3, data[1]);
        setEntryText(row, 4, data[2]);
        setEntryText(row, 5, data[3]);
        setEntryText(row, 6, data[4]);
        setEntryText(row, 7, data[5]);
        genderCombo->setCurrentText(data[6]);
    } else {
        setEntryText(row, 1, QString());
        setEntryText(row, 3, QString());
        setEntryText(row, 4, getNextMolecularNumber());
        setEntryText(row, 5, QString());
        setEntryText(row, 6, QString());
        setEntryText(row, 7, QString());
    }
    refreshCodeForRow(row);
    updateStats();
}

void ClinicalApp::deleteEntryRow()
{
    auto *button = qobject_cast<QPushButton *>(sender());
    if (!button) {
        return;
    }
    const int row = m_entryTable->indexAt(button->pos()).row();
    if (row >= 0) {
        m_entryTable->removeRow(row);
        updateStats();
    }
}

void ClinicalApp::handleEntryCellChanged(int row, int column)
{
    if (m_updating) {
        return;
    }

    if (column == 3) {
        const QString original = entryText(row, column);
        QString digitsOnly = original;
        digitsOnly.remove(QRegularExpression(QStringLiteral("\\D")));
        if (digitsOnly != original) {
            setEntryText(row, column, digitsOnly);
        }
    }

    if (column == 5 && !m_totalTable.isEmpty()) {
        const QString caseId = entryText(row, column).trimmed();
        if (!caseId.isEmpty() && caseId != QStringLiteral("0")) {
            const QList<CsvTable::Row> matches = m_totalTable.findEquals(QStringLiteral("病案号"), caseId);
            if (!matches.isEmpty()) {
                const QString oldMolecular = matches.first().value(QStringLiteral("分子号"));
                setEntryText(row, 4, oldMolecular);
                QMessageBox::information(this, QStringLiteral("随访识别"), QStringLiteral("分子号自动同步为: %1").arg(oldMolecular));
            }
        }
    }

    if (column == 2 || column == 3 || column == 4) {
        refreshCodeForRow(row);
    }
    updateStats();
}

void ClinicalApp::applyPrefixToTable()
{
    const QString prefix = m_prefixCombo->currentText();
    const QRegularExpression trailingDigits(QStringLiteral("(\\d+)$"));
    for (int row = 0; row < m_entryTable->rowCount(); ++row) {
        const QRegularExpressionMatch match = trailingDigits.match(entryText(row, 4));
        const QString number = match.hasMatch()
            ? match.captured(1).rightJustified(5, QLatin1Char('0'))
            : QString::number(row + 1).rightJustified(5, QLatin1Char('0'));
        setEntryText(row, 4, prefix + number);
        refreshCodeForRow(row);
    }
}

void ClinicalApp::resetEntryTable()
{
    if (QMessageBox::question(this, QStringLiteral("确认"), QStringLiteral("重置录入列表?")) != QMessageBox::Yes) {
        return;
    }
    m_entryTable->setRowCount(0);
    addEntryRow();
    updateStats();
}

void ClinicalApp::importToEntryTable()
{
    const QString path = QFileDialog::getOpenFileName(
        this,
        QStringLiteral("导入待入库数据"),
        QString(),
        QStringLiteral("CSV Files (*.csv);;All Files (*)"));
    if (path.isEmpty()) {
        return;
    }

    CsvTable importTable;
    QString error;
    if (!importTable.load(path, &error)) {
        QMessageBox::critical(this, QStringLiteral("导入失败"), error);
        return;
    }

    for (const CsvTable::Row &row : importTable.rows()) {
        const QString genderValue = row.value(QStringLiteral("性别"));
        const QString gender = (genderValue == QStringLiteral("男") || genderValue.compare(QStringLiteral("M"), Qt::CaseInsensitive) == 0)
            ? QStringLiteral("男")
            : ((genderValue == QStringLiteral("女") || genderValue.compare(QStringLiteral("F"), Qt::CaseInsensitive) == 0)
                ? QStringLiteral("女")
                : QStringLiteral("其他"));

        QString age = row.value(QStringLiteral("年龄"));
        age.remove(QRegularExpression(QStringLiteral("\\D")));

        addEntryRowFromData({
            row.value(QStringLiteral("姓名")),
            age,
            row.value(QStringLiteral("分子号")),
            row.value(QStringLiteral("病案号")),
            row.value(QStringLiteral("诊断")),
            row.value(QStringLiteral("诊断备注"), row.value(QStringLiteral("备注"))),
            gender
        });
    }
}

void ClinicalApp::exportForLabels()
{
    if (m_entryTable->rowCount() == 0) {
        return;
    }
    const QString today = QDate::currentDate().toString(QStringLiteral("yyyyMMdd"));
    const QString path = QFileDialog::getSaveFileName(
        this,
        QStringLiteral("导出标签"),
        QStringLiteral("标签_%1.csv").arg(today),
        QStringLiteral("CSV Files (*.csv);;All Files (*)"));
    if (path.isEmpty()) {
        return;
    }

    const QStringList headers = {
        QStringLiteral("姓名"),
        QStringLiteral("性别"),
        QStringLiteral("年龄"),
        QStringLiteral("分子号"),
        QStringLiteral("病案号"),
        QStringLiteral("诊断"),
        QStringLiteral("备注"),
        QStringLiteral("Code"),
        QStringLiteral("Len"),
        QStringLiteral("姓名2"),
        QStringLiteral("分子号2"),
        QStringLiteral("日期")
    };

    QList<CsvTable::Row> rows;
    for (int row = 0; row < m_entryTable->rowCount(); ++row) {
        const QString code = entryText(row, 8);
        CsvTable::Row out;
        out.insert(QStringLiteral("姓名"), entryText(row, 1));
        out.insert(QStringLiteral("性别"), genderAt(row));
        out.insert(QStringLiteral("年龄"), entryText(row, 3));
        out.insert(QStringLiteral("分子号"), entryText(row, 4));
        out.insert(QStringLiteral("病案号"), entryText(row, 5));
        out.insert(QStringLiteral("诊断"), entryText(row, 6));
        out.insert(QStringLiteral("备注"), entryText(row, 7));
        out.insert(QStringLiteral("Code"), code);
        out.insert(QStringLiteral("Len"), QString::number(code.size()));
        out.insert(QStringLiteral("姓名2"), entryText(row, 1));
        out.insert(QStringLiteral("分子号2"), entryText(row, 4));
        out.insert(QStringLiteral("日期"), today);
        rows.append(out);
    }

    CsvTable writer;
    QString error;
    if (!writer.saveRows(path, headers, rows, &error)) {
        QMessageBox::critical(this, QStringLiteral("导出失败"), error);
    }
}

void ClinicalApp::writeToDatabase()
{
    if (m_dbPath.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("提示"), QStringLiteral("请先连接总库"));
        return;
    }

    const QString today = QDate::currentDate().toString(QStringLiteral("yyyyMMdd"));
    int saved = 0;
    for (int row = 0; row < m_entryTable->rowCount(); ++row) {
        const QString name = entryText(row, 1).trimmed();
        if (name.isEmpty()) {
            continue;
        }
        CsvTable::Row out;
        out.insert(QStringLiteral("姓名"), name);
        out.insert(QStringLiteral("性别"), genderAt(row));
        out.insert(QStringLiteral("年龄"), entryText(row, 3));
        out.insert(QStringLiteral("分子号"), entryText(row, 4));
        out.insert(QStringLiteral("病案号"), entryText(row, 5));
        out.insert(QStringLiteral("诊断"), entryText(row, 6));
        out.insert(QStringLiteral("诊断备注"), entryText(row, 7));
        out.insert(QStringLiteral("Code"), entryText(row, 8));
        out.insert(QStringLiteral("日期"), today);
        m_totalTable.append(out);
        ++saved;
    }

    if (saved == 0) {
        return;
    }

    ensureDatabaseHeaders();
    QString error;
    if (!m_totalTable.save(m_dbPath, &error)) {
        QMessageBox::critical(this, QStringLiteral("写入失败"), error);
        return;
    }

    QMessageBox::information(this, QStringLiteral("成功"), QStringLiteral("总库已同步。"));
    m_entryTable->setRowCount(0);
    addEntryRow();
}

void ClinicalApp::searchDatabase()
{
    const QString keyword = m_scanInput->text().trimmed();
    if (m_totalTable.isEmpty() || keyword.isEmpty()) {
        return;
    }
    displayOut(m_totalTable.findContains(m_searchColumnCombo->currentText(), keyword), true);
}

void ClinicalApp::handleBarcodeScan()
{
    const QString code = m_scanInput->text().trimmed();
    m_scanInput->clear();
    if (m_totalTable.isEmpty() || code.isEmpty()) {
        return;
    }
    const QList<CsvTable::Row> matches = m_totalTable.findEquals(QStringLiteral("Code"), code);
    if (!matches.isEmpty()) {
        displayOut(matches, false);
    }
}

void ClinicalApp::exportOutResults()
{
    if (m_outTable->rowCount() == 0) {
        return;
    }
    const QString path = QFileDialog::getSaveFileName(
        this,
        QStringLiteral("保存检索结果"),
        QStringLiteral("结果导出.csv"),
        QStringLiteral("CSV Files (*.csv);;All Files (*)"));
    if (path.isEmpty()) {
        return;
    }

    QList<CsvTable::Row> rows;
    for (int row = 0; row < m_outTable->rowCount(); ++row) {
        CsvTable::Row out;
        for (int column = 0; column < kOutHeaders.size(); ++column) {
            out.insert(kOutHeaders[column], cellText(m_outTable, row, column));
        }
        rows.append(out);
    }

    CsvTable writer;
    QString error;
    if (!writer.saveRows(path, kOutHeaders, rows, &error)) {
        QMessageBox::critical(this, QStringLiteral("保存失败"), error);
    }
}

void ClinicalApp::displayOut(const QList<CsvTable::Row> &rows, bool clear)
{
    if (clear) {
        m_outTable->setRowCount(0);
    }

    const QStringList sourceHeaders = kDbHeaders.mid(0, 8);
    for (const CsvTable::Row &source : rows) {
        const int row = m_outTable->rowCount();
        m_outTable->insertRow(row);
        for (int column = 0; column < sourceHeaders.size(); ++column) {
            m_outTable->setItem(row, column, new QTableWidgetItem(source.value(sourceHeaders[column])));
        }
        const QString code = source.value(QStringLiteral("Code"));
        m_outTable->setItem(row, 8, new QTableWidgetItem(decodeCollectionTime(code)));
        m_outTable->setItem(row, 9, new QTableWidgetItem(source.value(QStringLiteral("日期"))));
    }
}

void ClinicalApp::updateStats()
{
    const int total = m_entryTable->rowCount();
    int male = 0;
    int female = 0;
    for (int row = 0; row < total; ++row) {
        const QString gender = genderAt(row);
        if (gender == QStringLiteral("男")) {
            ++male;
        } else if (gender == QStringLiteral("女")) {
            ++female;
        }
    }
    m_statTotal->setText(QStringLiteral("待入库 %1").arg(total));
    m_statMale->setText(QStringLiteral("男 %1").arg(male));
    m_statFemale->setText(QStringLiteral("女 %1").arg(female));
}

void ClinicalApp::refreshCodeForRow(int row)
{
    setEntryText(row, 8, calculateRowCode(row));
}

QString ClinicalApp::calculateRowCode(int row) const
{
    const QString molecular = entryText(row, 4);
    const QRegularExpressionMatch match = QRegularExpression(QStringLiteral("\\d+$")).match(molecular);
    const int number = match.hasMatch() ? match.captured(0).toInt() : 0;
    const QString part1 = toBase32(number);

    const QString gender = genderAt(row);
    const QString genderCode = gender == QStringLiteral("男") ? QStringLiteral("M") : (gender == QStringLiteral("女") ? QStringLiteral("F") : QStringLiteral("G"));
    const QString ageText = entryText(row, 3);
    const int age = qMin(ageText.toInt(), 99);
    const QString part2 = QStringLiteral("%1%2").arg(genderCode, QString::number(age).rightJustified(2, QLatin1Char('0')));

    const QDate today = QDate::currentDate();
    const QString part3 = QStringLiteral("%1%2").arg(QString::number(today.year()).right(2), getMonthCode(today.month()));
    const QString prefix = (!molecular.isEmpty() && molecular[0].isLetter()) ? QString(molecular[0]).toUpper() : QStringLiteral("K");
    return part1 + part2 + part3 + prefix + QStringLiteral("V1");
}

QString ClinicalApp::decodeCollectionTime(const QString &code) const
{
    if (code.size() < 9) {
        return {};
    }
    const QString year = QStringLiteral("20") + code.mid(6, 2);
    const QChar monthChar = code[8];
    const QString month = monthChar.isDigit()
        ? QString(monthChar).rightJustified(2, QLatin1Char('0'))
        : QString::number(monthChar.toLatin1() - 55).rightJustified(2, QLatin1Char('0'));
    return year + month;
}

QString ClinicalApp::getNextMolecularNumber() const
{
    const QString prefix = m_prefixCombo->currentText();
    int maxNumber = 0;
    const QRegularExpression trailingDigits(QStringLiteral("(\\d+)$"));
    for (int row = 0; row < m_entryTable->rowCount(); ++row) {
        const QRegularExpressionMatch match = trailingDigits.match(entryText(row, 4));
        if (match.hasMatch()) {
            maxNumber = qMax(maxNumber, match.captured(1).toInt());
        }
    }
    return prefix + QString::number(maxNumber + 1).rightJustified(5, QLatin1Char('0'));
}

QString ClinicalApp::toBase32(int n) const
{
    if (n == 0) {
        return QStringLiteral("000");
    }

    QString result;
    while (n > 0) {
        result.prepend(kBase32Chars[n % 32]);
        n /= 32;
    }
    return result.rightJustified(3, QLatin1Char('0'));
}

QString ClinicalApp::getMonthCode(int month) const
{
    return month < 10 ? QString::number(month) : QString(QChar(55 + month));
}

QString ClinicalApp::cellText(QTableWidget *table, int row, int column) const
{
    const QTableWidgetItem *item = table->item(row, column);
    return item ? item->text() : QString();
}

QString ClinicalApp::entryText(int row, int column) const
{
    return cellText(m_entryTable, row, column);
}

QString ClinicalApp::genderAt(int row) const
{
    auto *combo = qobject_cast<QComboBox *>(m_entryTable->cellWidget(row, 2));
    return combo ? combo->currentText() : QString();
}

void ClinicalApp::setEntryText(int row, int column, const QString &text)
{
    const QSignalBlocker blocker(m_entryTable);
    if (!m_entryTable->item(row, column)) {
        m_entryTable->setItem(row, column, new QTableWidgetItem(text));
    } else {
        m_entryTable->item(row, column)->setText(text);
    }
}

void ClinicalApp::ensureDatabaseHeaders()
{
    m_totalTable.ensureHeaders(kDbHeaders);
}
