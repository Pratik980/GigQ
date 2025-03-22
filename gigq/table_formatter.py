"""
Table formatting utilities for GigQ CLI output.

This module replaces the external tabulate dependency with standard library code.
It should be placed at: gigq/table_formatter.py
"""


def format_table(rows, headers=None):
    """
    Format a list of rows as a text table.

    Args:
        rows: List of rows, where each row is a list of values
        headers: Optional list of header values

    Returns:
        Formatted table as a string
    """
    if not rows:
        return "No data to display."

    # Convert all values to strings
    str_rows = [[str(cell) for cell in row] for row in rows]

    # Determine the maximum number of columns
    max_cols = max([len(row) for row in str_rows]) if str_rows else 0
    if headers:
        max_cols = max(max_cols, len(headers))

    # Pad rows to ensure they all have the same number of columns
    padded_rows = []
    for row in str_rows:
        padded_row = row.copy()
        while len(padded_row) < max_cols:
            padded_row.append("")
        padded_rows.append(padded_row)

    # Add headers if provided
    all_rows = padded_rows
    if headers:
        header_row = list(headers)
        while len(header_row) < max_cols:
            header_row.append("")
        all_rows = [header_row] + padded_rows

    # Calculate column widths
    col_widths = [0] * max_cols
    for row in all_rows:
        for i in range(min(len(row), max_cols)):
            col_widths[i] = max(col_widths[i], len(row[i]))

    # Add padding to column widths
    col_widths = [width + 2 for width in col_widths]

    # Create separator line
    separator = "+" + "+".join("-" * width for width in col_widths) + "+"

    # Format rows
    result = [separator]
    for i, row in enumerate(all_rows):
        # Format the row
        cells = []
        for j in range(max_cols):
            cell = row[j] if j < len(row) else ""
            width = col_widths[j]
            cells.append(f" {cell.ljust(width - 2)} ")

        row_str = "|" + "|".join(cells) + "|"
        result.append(row_str)

        # Add separator after header if headers were provided
        if headers and i == 0:
            result.append(separator)

    result.append(separator)
    return "\n".join(result)


def simple_table(rows, headers=None):
    """
    Format a simpler table without borders, just aligned columns.
    Useful for less complex output needs.

    Args:
        rows: List of rows, where each row is a list of values
        headers: Optional list of header values

    Returns:
        Formatted table as a string
    """
    if not rows:
        return "No data to display."

    # Convert all values to strings
    str_rows = [[str(cell) for cell in row] for row in rows]

    # Determine max columns
    max_cols = max([len(row) for row in str_rows]) if str_rows else 0
    if headers:
        max_cols = max(max_cols, len(headers))

    # Pad rows
    padded_rows = []
    for row in str_rows:
        padded_row = row.copy()
        while len(padded_row) < max_cols:
            padded_row.append("")
        padded_rows.append(padded_row)

    # Use headers if provided
    all_rows = padded_rows
    if headers:
        header_row = list(headers)
        while len(header_row) < max_cols:
            header_row.append("")
        all_rows = [header_row] + padded_rows

    # Calculate column widths
    col_widths = [0] * max_cols
    for row in all_rows:
        for i in range(min(len(row), max_cols)):
            col_widths[i] = max(col_widths[i], len(row[i]))

    # Format rows
    result = []
    for i, row in enumerate(all_rows):
        # Format cells
        cells = []
        for j in range(max_cols):
            cell = row[j] if j < len(row) else ""
            width = col_widths[j]
            cells.append(cell.ljust(width))

        row_str = " ".join(cells)
        result.append(row_str)

        # Add separator after header if headers were provided
        if headers and i == 0:
            result.append("-" * sum(col_widths))

    return "\n".join(result)
