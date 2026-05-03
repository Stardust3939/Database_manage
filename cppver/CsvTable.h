#pragma once

#include <QList>
#include <QMap>
#include <QString>
#include <QStringList>

class CsvTable
{
public:
    using Row = QMap<QString, QString>;

    bool load(const QString &path, QString *error = nullptr);
    bool save(const QString &path, QString *error = nullptr) const;
    bool saveRows(const QString &path, const QStringList &headers, const QList<Row> &rows, QString *error = nullptr) const;

    void append(const Row &row);
    void ensureHeaders(const QStringList &headers);
    bool isEmpty() const;
    int size() const;
    void clear();

    const QStringList &headers() const;
    const QList<Row> &rows() const;
    QList<Row> findContains(const QString &column, const QString &keyword) const;
    QList<Row> findEquals(const QString &column, const QString &value) const;

    static QStringList parseLine(const QString &line);
    static QString formatLine(const QStringList &fields);

private:
    QStringList m_headers;
    QList<Row> m_rows;
};
