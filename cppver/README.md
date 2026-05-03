# Clinical Data Management System - C++/Qt

This is a native C++/Qt 6 port of the Python/PyQt clinical data management tool.

## Build

Run from the repository root:

```bat
cppver\build_msvc.bat
```

The script uses:

- Qt: `C:\Qt\6.8.3\msvc2022_64`
- CMake: `C:\Qt\Tools\CMake_64\bin\cmake.exe`
- MSVC environment: Visual Studio Build Tools `vcvars64.bat`

The runnable executable is generated at:

```text
cppver\build\clinsys_cpp.exe
```

`windeployqt` is run automatically so the Qt runtime files are copied next to the executable.

## Data Format

This version uses UTF-8 CSV files for the database, imports, label exports, and search exports. Excel can open and save these CSV files directly.

The original Python version used pandas to read/write `.xlsx`; this Qt installation does not include ActiveQt, and Qt Widgets does not provide native `.xlsx` support by itself.

