"""Tests for the CLI with the custom table formatter.

This test file should be placed at: tests/test_cli_formatter.py
It validates that the CLI formatting works correctly without tabulate.
"""

import os
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from gigq import Job, JobQueue
from gigq.cli import cmd_list, cmd_status


def example_function(value=1):
    """Example function for testing."""
    return {"result": value * 2}


class TestCLI(unittest.TestCase):
    """Tests for the CLI module using the custom table formatter."""

    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.queue = JobQueue(self.db_path)
        
        # Add some test jobs
        for i in range(3):
            job = Job(name=f"test_job_{i}", function=example_function, params={"value": i})
            self.queue.submit(job)

    def tearDown(self):
        """Clean up the temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_cmd_list(self):
        """Test the list command with the custom table formatter."""
        # Redirect stdout to capture output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        # Run the list command
        cmd_list(type('Args', (), {
            'db': self.db_path,
            'status': None,
            'limit': 100
        }))
        
        # Reset stdout
        sys.stdout = sys.__stdout__
        
        # Check that the output is formatted correctly
        output = captured_output.getvalue()
        
        # Should have a table with borders
        self.assertIn("+", output)
        self.assertIn("|", output)
        
        # Should contain all job names
        for i in range(3):
            self.assertIn(f"test_job_{i}", output)
        
        # Should contain the headers
        self.assertIn("ID", output)
        self.assertIn("Name", output)
        self.assertIn("Status", output)
        self.assertIn("Priority", output)
        self.assertIn("Created", output)
        self.assertIn("Updated", output)

    def test_cmd_status_with_executions(self):
        """Test the status command with executions table."""
        # Create a job and process it to generate execution history
        job = Job(name="execution_test", function=example_function, params={"value": 42})
        job_id = self.queue.submit(job)
        
        # Process the job
        from gigq import Worker
        worker = Worker(self.db_path)
        worker.process_one()
        
        # Redirect stdout to capture output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        # Run the status command with executions
        cmd_status(type('Args', (), {
            'db': self.db_path,
            'job_id': job_id,
            'show_params': False,
            'show_result': False,
            'show_executions': True
        }))
        
        # Reset stdout
        sys.stdout = sys.__stdout__
        
        # Check that the output is formatted correctly
        output = captured_output.getvalue()
        
        # Basic job info should be there
        self.assertIn("execution_test", output)
        self.assertIn("completed", output.lower())
        
        # Executions table should be there
        self.assertIn("Executions:", output)
        self.assertIn("ID", output)
        self.assertIn("Started", output)
        self.assertIn("Completed", output)
        self.assertIn("Status", output)

    def test_integration_with_cli_module(self):
        """Test integration with the CLI module."""
        # Test importing the module doesn't crash
        with patch.object(sys, 'argv', ['gigq', '--db', self.db_path, 'list']):
            from gigq.cli import main
            
            # Redirect stdout to capture output
            captured_output = StringIO()
            sys.stdout = captured_output
            
            # Run the command
            try:
                main()
            except SystemExit:
                pass
            
            # Reset stdout
            sys.stdout = sys.__stdout__
            
            # Check output
            output = captured_output.getvalue()
            self.assertIn("test_job_0", output)


if __name__ == "__main__":
    unittest.main()