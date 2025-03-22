"""Tests for the CLI with the custom table formatter.

This test file validates that the CLI formatting works correctly without tabulate.
"""

import os
import sys
import tempfile
import unittest
import sqlite3
from io import StringIO
from unittest.mock import patch, MagicMock

from gigq import Job, JobQueue
from gigq.cli import cmd_list, cmd_status, format_time


def example_function(value=1):
    """Example function for testing."""
    return {"result": value * 2}


class TestCLIFormatter(unittest.TestCase):
    """Tests for the CLI module using the custom table formatter."""

    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.queue = JobQueue(self.db_path)

        # Add some test jobs
        for i in range(3):
            job = Job(
                name=f"test_job_{i}", function=example_function, params={"value": i}
            )
            self.queue.submit(job)

        # Save original stdout
        self.original_stdout = sys.stdout

    def tearDown(self):
        """Clean up the temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

        # Restore stdout
        sys.stdout = self.original_stdout

    def test_cmd_list_formatting(self):
        """Test the list command formatting."""
        # Redirect stdout to capture output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Create mock args
        args = MagicMock()
        args.db = self.db_path
        args.status = None
        args.limit = 100

        # Run the list command
        cmd_list(args)

        # Check the output format
        output = captured_output.getvalue()

        # Should have proper table formatting with borders
        self.assertIn("+", output)  # Border characters
        self.assertIn("|", output)  # Column separators

        # Should have headers
        self.assertIn("ID", output)
        self.assertIn("Name", output)
        self.assertIn("Status", output)
        self.assertIn("Priority", output)

        # Should contain all job names
        for i in range(3):
            self.assertIn(f"test_job_{i}", output)

    def test_cmd_status_with_executions(self):
        """Test the status command with executions table."""
        # Create a job and process it to generate execution history
        job = Job(
            name="execution_test", function=example_function, params={"value": 42}
        )
        job_id = self.queue.submit(job)

        # Manually add execution record
        conn = sqlite3.connect(self.db_path)
        execution_id = "test-execution-id"
        now = format_time(None).replace("-", "")  # Just need any valid timestamp format

        conn.execute(
            """
            INSERT INTO job_executions (
                id, job_id, worker_id, status, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (execution_id, job_id, "test-worker", "completed", now, now),
        )
        conn.commit()
        conn.close()

        # Redirect stdout to capture output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Create mock args
        args = MagicMock()
        args.db = self.db_path
        args.job_id = job_id
        args.show_params = False
        args.show_result = False
        args.show_executions = True

        # Run the status command
        cmd_status(args)

        # Check the output format
        output = captured_output.getvalue()

        # Basic job info should be there
        self.assertIn("execution_test", output)

        # Executions table should be formatted properly
        self.assertIn("Executions:", output)
        self.assertIn("+", output)  # Border characters
        self.assertIn("|", output)  # Column separators
        self.assertIn("ID", output)
        self.assertIn("Started", output)
        self.assertIn("test-execution-id", output)

    def test_format_time_function(self):
        """Test the format_time function."""
        # Test with None
        self.assertEqual(format_time(None), "-")

        # Test with valid ISO format
        timestamp = "2023-01-01T12:34:56"
        formatted = format_time(timestamp)
        self.assertEqual(formatted, "2023-01-01 12:34:56")

        # Test with invalid format
        invalid = "not-a-timestamp"
        self.assertEqual(format_time(invalid), invalid)


if __name__ == "__main__":
    unittest.main()
