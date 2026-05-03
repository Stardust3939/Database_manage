#pragma once

#include "CsvTable.h"

#include <QMainWindow>
#include <QTableWidget>

class QComboBox;
class QLabel;
class QLineEdit;
class QPushButton;

class ClinicalApp : public QMainWindow
{
public:
    explicit ClinicalApp(QWidget *parent = nullptr);

private:
    void connectDatabase();
    void addEntryRow();
    void deleteEntryRow();
    void handleEntryCellChanged(int row, int column);
    void applyPrefixToTable();
    void resetEntryTable();
    void importToEntryTable();
    void exportForLabels();
    void writeToDatabase();
    void searchDatabase();
    void handleBarcodeScan();
    void exportOutResults();

    void setupUi();
    void initStockInUi(QWidget *tab);
    void initStockOutUi(QWidget *tab);
    void addEntryRowFromData(const QStringList &data);
    void displayOut(const QList<CsvTable::Row> &rows, bool clear);
    void updateStats();
    void refreshCodeForRow(int row);

    QString calculateRowCode(int row) const;
    QString decodeCollectionTime(const QString &code) const;
    QString getNextMolecularNumber() const;
    QString toBase32(int n) const;
    QString getMonthCode(int month) const;
    QString cellText(QTableWidget *table, int row, int column) const;
    QString entryText(int row, int column) const;
    QString genderAt(int row) const;
    void setEntryText(int row, int column, const QString &text);
    void ensureDatabaseHeaders();

    QString m_dbPath;
    CsvTable m_totalTable;

    QLabel *m_dbStatusLabel = nullptr;
    QLabel *m_statTotal = nullptr;
    QLabel *m_statMale = nullptr;
    QLabel *m_statFemale = nullptr;
    QComboBox *m_prefixCombo = nullptr;
    QComboBox *m_searchColumnCombo = nullptr;
    QLineEdit *m_scanInput = nullptr;
    QTableWidget *m_entryTable = nullptr;
    QTableWidget *m_outTable = nullptr;
    bool m_updating = false;
};
