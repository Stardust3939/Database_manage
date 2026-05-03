#include "ClinicalApp.h"

#include <QApplication>
#include <QFont>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setFont(QFont(QStringLiteral("Microsoft YaHei"), 9));

    ClinicalApp window;
    window.show();

    return app.exec();
}

