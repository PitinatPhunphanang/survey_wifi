"""
storage/excel.py
Excel file helpers: resolve a writable output path and append/create sheets.
"""
import os
from datetime import datetime

import pandas as pd


def resolve_output_file(preferred_file: str) -> str:
    """
    Return preferred_file if writable, otherwise return an autosave path.
    This avoids crashing when the workbook is open in Excel.
    """
    if not os.path.exists(preferred_file):
        return preferred_file

    try:
        with open(preferred_file, "a+b"):
            return preferred_file
    except PermissionError:
        base, ext = os.path.splitext(preferred_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_autosave_{timestamp}{ext}"


def save_to_excel(file_name: str, sheet_name: str, df: pd.DataFrame):
    """
    Append df to sheet_name in file_name, creating the file/sheet if needed.
    Stale columns (present in file but not in df) are silently dropped.
    """
    try:
        if not os.path.exists(file_name):
            with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            return

        try:
            existing_df = pd.read_excel(file_name, sheet_name=sheet_name)
            # Keep only columns that still exist in the incoming df
            existing_df = existing_df[[c for c in existing_df.columns if c in df.columns]]
            updated_df = pd.concat([existing_df, df], ignore_index=True)
        except ValueError:
            updated_df = df

        with pd.ExcelWriter(
            file_name,
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace",
        ) as writer:
            updated_df.to_excel(writer, sheet_name=sheet_name, index=False)

    except PermissionError as exc:
        raise PermissionError(
            f"Cannot write to '{file_name}'. Please close the Excel file and try again."
        ) from exc
