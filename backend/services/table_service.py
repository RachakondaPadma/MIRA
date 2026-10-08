import os
import pandas as pd


def read_table(file_path):
    """
    Read CSV or Excel file into a pandas DataFrame.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("Table file not found.")

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".csv":
        df = pd.read_csv(file_path)

    elif extension in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)

    else:
        raise ValueError(
            "Unsupported table format. Use CSV, XLSX or XLS."
        )

    if df.empty:
        raise ValueError("The table is empty.")

    # Remove completely empty rows/columns
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    return df


def table_summary(df):
    """
    Generate useful information about the table.
    """
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(column) for column in df.columns],
        "numeric_columns": [str(column) for column in numeric_columns]
    }

    return summary


def table_preview(df, rows=10):
    """
    Convert first rows into JSON-friendly data.
    """
    preview = df.head(rows).copy()

    preview = preview.where(
        pd.notnull(preview),
        None
    )

    return preview.to_dict(orient="records")


def find_numeric_extremes(df):
    """
    Find minimum and maximum values for numeric columns.
    """
    result = {}

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    for column in numeric_columns:
        series = df[column].dropna()

        if series.empty:
            continue

        result[str(column)] = {
            "minimum": float(series.min()),
            "maximum": float(series.max())
        }

    return result