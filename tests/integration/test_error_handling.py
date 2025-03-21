"""Tests for error handling and job recovery."""

import os
import tempfile
import sqlite3
from gigq import Job, JobStatus
from tests.integration.base import IntegrationTestBase
from tests.job_functions import retry_job, failing_job


class TestErrorHandlingAndRecovery(IntegrationTestBase):
    """Test error handling and job recovery."""

    def test_job_retry_on_failure(self):
        # Create a SQLite database for tracking attempts
        _, tracker_db_path = tempfile.mkstemp(suffix=".db")
        os.close(_)  # Close the file descriptor

        # Register for cleanup
        self.addCleanup(
            lambda: os.path.exists(tracker_db_path) and os.unlink(tracker_db_path)
        )

        # Initialize the tracking database
        conn = sqlite3.connect(tracker_db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS attempts (job_id TEXT PRIMARY KEY, count INTEGER)"
        )
        conn.commit()
        conn.close()

        # Create a job with retry using the SQLite tracker
        job = Job(
            name="failing_job",
            function=retry_job,
            params={"job_id": "test1", "fail_times": 1, "state_db": tracker_db_path},
            max_attempts=3,
        )

        # Submit the job
        job_id = self.queue.submit(job)

        # Process the job (should fail first time)
        self.worker.process_one()

        # Check status (should be pending for retry)
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.PENDING.value)
        self.assertEqual(status["attempts"], 1)

        # Process again (should succeed)
        self.worker.process_one()

        # Check final status
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status["attempts"], 2)
        self.assertEqual(status["result"]["attempts"], 2)

    def test_job_max_attempts_exceeded(self):
        # Create a job that will always fail
        job = Job(name="always_failing_job", function=failing_job, max_attempts=2)

        # Submit the job
        job_id = self.queue.submit(job)

        # Process the job twice (should fail both times)
        self.worker.process_one()  # First attempt

        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.PENDING.value)
        self.assertEqual(status["attempts"], 1)

        self.worker.process_one()  # Second attempt

        # Check final status - should be failed after max attempts
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.FAILED.value)
        self.assertEqual(status["attempts"], 2)
        self.assertIn("designed to fail", status["error"])
