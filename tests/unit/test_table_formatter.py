"""
Unit tests for the table formatter utilities in GigQ.
"""

import unittest
from gigq.table_formatter import format_table, simple_table


class TestTableFormatter(unittest.TestCase):
    """Tests for the table formatter utilities."""

    def test_format_table_with_headers(self):
        """Test that a table can be formatted with headers."""
        headers = ["ID", "Name", "Status"]
        rows = [
            ["1", "Job A", "Running"],
            ["2", "Job B", "Completed"],
            ["3", "Job C with a long name", "Pending"],
        ]

        result = format_table(rows, headers)

        # Assert basic structure
        self.assertTrue(result.startswith("+"))
        self.assertTrue(result.endswith("+"))

        # Check that all data appears in the result
        for row in rows:
            for cell in row:
                self.assertIn(cell, result)

        for header in headers:
            self.assertIn(header, result)

        # Check that there's a separator after the header
        lines = result.split("\n")
        self.assertEqual(
            lines[0], lines[2]
        )  # First separator equals the one after header

        # Check proper number of lines - update to match actual output
        # Top border + header row + separator + data rows (3) + bottom border = 7 lines
        self.assertEqual(len(lines), 7)

    def test_format_table_without_headers(self):
        """Test that a table can be formatted without headers."""
        rows = [["1", "Job A", "Running"], ["2", "Job B", "Completed"]]

        result = format_table(rows)

        # Check structure
        lines = result.split("\n")
        # For a table without headers, we expect:
        # 1. top border
        # 2. first row
        # 3. second row
        # 4. bottom border
        # = 4 lines total
        self.assertEqual(len(lines), 4)  # top border + 2 data rows + bottom border = 4

        # Check that all data appears in the result
        for row in rows:
            for cell in row:
                self.assertIn(cell, result)

    def test_format_table_empty(self):
        """Test handling of empty data."""
        result = format_table([])
        self.assertEqual(result, "No data to display.")

    def test_format_table_varying_row_lengths(self):
        """Test that rows with different lengths are handled correctly."""
        rows = [
            ["1", "Job A", "Running", "Extra"],
            ["2", "Job B"],
            ["3", "Job C", "Pending", "Extra", "More Extra"],
        ]

        result = format_table(rows)

        # Should not crash and should contain all data
        for row in rows:
            for cell in row:
                self.assertIn(cell, result)

    def test_simple_table_with_headers(self):
        """Test the simple table format with headers."""
        headers = ["ID", "Name", "Status"]
        rows = [["1", "Job A", "Running"], ["2", "Job B", "Completed"]]

        result = simple_table(rows, headers)

        # Check that all data appears in the result
        for row in rows:
            for cell in row:
                self.assertIn(cell, result)

        for header in headers:
            self.assertIn(header, result)

        # Check that there's a separator after the header
        lines = result.split("\n")
        separator_line = lines[1]
        self.assertTrue(all(c == "-" for c in separator_line))

        # Check correct number of lines
        expected_lines = 1 + 1 + len(rows)  # header + separator + data rows
        self.assertEqual(len(lines), expected_lines)

    def test_simple_table_without_headers(self):
        """Test the simple table format without headers."""
        rows = [["1", "Job A", "Running"], ["2", "Job B", "Completed"]]

        result = simple_table(rows)

        # Check that there's no separator (just the data rows)
        lines = result.split("\n")
        expected_lines = len(rows)  # just data rows
        self.assertEqual(len(lines), expected_lines)

        # Check that all data appears in the result
        for row in rows:
            for cell in row:
                self.assertIn(cell, result)

    def test_simple_table_empty(self):
        """Test handling of empty data in simple table."""
        result = simple_table([])
        self.assertEqual(result, "No data to display.")


if __name__ == "__main__":
    unittest.main()
