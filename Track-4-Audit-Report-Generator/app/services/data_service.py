import io
import pandas as pd


def parse_uploaded_file(filename: str, file_bytes: bytes) -> str:
    """
    Parse a CSV or Excel file and return a plain-text summary
    suitable for passing to the Claude prompt.
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    lines = [
        f"Columns: {', '.join(df.columns.tolist())}",
        f"Total rows: {len(df)}",
        "",
        "Sample data (first 20 rows):",
        df.head(20).to_string(index=False),
    ]

    # Basic stats for numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        lines.append("")
        lines.append("Numeric column statistics:")
        lines.append(df[numeric_cols].describe().to_string())

    return "\n".join(lines)
