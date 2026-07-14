"""Force a full Microsoft Excel recalculation of a workbook copy on Windows."""

from __future__ import annotations

import argparse
from pathlib import Path

import win32com.client


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    workbook_path = str(args.workbook.resolve())

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    book = None
    try:
        book = excel.Workbooks.Open(workbook_path)
        excel.CalculateFullRebuild()
        book.Save()
        return 0
    finally:
        if book is not None:
            book.Close(SaveChanges=False)
        excel.Quit()


if __name__ == "__main__":
    raise SystemExit(main())
