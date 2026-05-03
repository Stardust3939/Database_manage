#include "CsvTable.h"

#include <QFile>
#include <QRegularExpression>
#include <QSaveFile>
#include <QTextStream>

bool CsvTable::load(const QString &path, QString *error)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (error) {
            *error = file.errorString();
        }
        return false;
    }

    QTextStream in(&file);
    in.setEncoding(QStringConverter::Utf8);

    clear();
    if (in.atEnd()) {
        return true;
    }

    QString headerLine = in.readLine();
    if (headerLine.startsWith(QChar(0xfeff))) {
        headerLine.remove(0, 1);
    }
    m_headers = parseLine(headerLine);

    while (!in.atEnd()) {
        const QString line = in.readLine();
        if (line.trimmed().isEmpty()) {
            continue;
        }
        const QStringList fields = parseLine(line);
        Row row;
        for (int i = 0; i < m_headers.size(); ++i) {
            row.insert(m_headers[i], i < fields.size() ? fields[i] : QString());
        }
        m_rows.append(row);
    }

    return true;
}

bool CsvTable::save(const QString &path, QString *error) const
{
    return saveRows(path, m_headers, m_rows, error);
}

bool CsvTable::saveRows(const QString &path, const QStringList &headers, const QList<Row> &rows, QString *error) const
{
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (error) {
            *error = file.errorString();
        }
        return false;
    }

    QTextStream out(&file);
    out.setEncoding(QStringConverter::Utf8);
    out << QChar(0xfeff);
    out << formatLine(headers) << '\n';
    for (const Row &row : rows) {
        QStringList fields;
        fields.reserve(headers.size());
        for (const QString &header : headers) {
            fields << row.value(header);
        }
        out << formatLine(fields) << '\n';
    }

    if (!file.commit()) {
        if (error) {
            *error = file.errorString();
        }
        return false;
    }
    return true;
}

void CsvTable::append(const Row &row)
{
    for (auto it = row.cbegin(); it != row.cend(); ++it) {
        if (!m_headers.contains(it.key())) {
            m_headers.append(it.key());
        }
    }
    m_rows.append(row);
}

void CsvTable::ensureHeaders(const QStringList &headers)
{
    for (const QString &header : headers) {
        if (!m_headers.contains(header)) {
            m_headers.append(header);
        }
    }
}

bool CsvTable::isEmpty() const
{
    return m_rows.isEmpty();
}

int CsvTable::size() const
{
    return m_rows.size();
}

void CsvTable::clear()
{
    m_headers.clear();
    m_rows.clear();
}

const QStringList &CsvTable::headers() const
{
    return m_headers;
}

const QList<CsvTable::Row> &CsvTable::rows() const
{
    return m_rows;
}

QList<CsvTable::Row> CsvTable::findContains(const QString &column, const QString &keyword) const
{
    QList<Row> result;
    for (const Row &row : m_rows) {
        if (row.value(column).contains(keyword, Qt::CaseInsensitive)) {
            result.append(row);
        }
    }
    return result;
}

QList<CsvTable::Row> CsvTable::findEquals(const QString &column, const QString &value) const
{
    QList<Row> result;
    for (const Row &row : m_rows) {
        if (row.value(column) == value) {
            result.append(row);
        }
    }
    return result;
}

QStringList CsvTable::parseLine(const QString &line)
{
    QStringList fields;
    QString current;
    bool quoted = false;

    for (int i = 0; i < line.size(); ++i) {
        const QChar ch = line[i];
        if (ch == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
                current += '"';
                ++i;
            } else {
                quoted = !quoted;
            }
        } else if (ch == ',' && !quoted) {
            fields << current;
            current.clear();
        } else {
            current += ch;
        }
    }
    fields << current;
    return fields;
}

QString CsvTable::formatLine(const QStringList &fields)
{
    QStringList escaped;
    escaped.reserve(fields.size());
    for (QString field : fields) {
        if (field.contains('"')) {
            field.replace('"', "\"\"");
        }
        if (field.contains(',') || field.contains('"') || field.contains('\n') || field.contains('\r')) {
            field = '"' + field + '"';
        }
        escaped << field;
    }
    return escaped.join(',');
}
