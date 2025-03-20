"""Tests for job timeout handling."""
import time
import sqlite3
from datetime import datetime, timedelta
from gigq import Job, JobStatus, Worker
from tests.integration.base import IntegrationTestBase
from tests.job_functions import sleep_job

class TestTimeoutHandling(IntegrationTestBase):
    """Test timeout handling for long-running jobs."""
    
    def test_job_timeout_detection(self):
        """Test that jobs are properly marked as timed out."""
        # Create and submit a job
        job = Job(
            name="timeout_job",
            function=sleep_job,
            params={"duration": 2},  # This doesn't really matter for the test
            timeout=1,  # 1 second timeout
            max_attempts=2
        )
        job_id = self.queue.submit(job)
        
        # Manually modify the database to make the job appear as "running"
        # and started long enough ago to have timed out
        conn = sqlite3.connect(self.db_path)
        started_at = (datetime.now() - timedelta(seconds=10)).isoformat()  # 10 seconds ago
        
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, started_at = ?, worker_id = ?
            WHERE id = ?
            """,
            (JobStatus.RUNNING.value, started_at, "fake-worker", job_id)
        )
        conn.commit()
        conn.close()
        
        # Now check for timeouts - this should detect our fake running job as timed out
        another_worker = Worker(self.db_path)
        another_worker._check_for_timeouts()
        
        # Check job status - should be marked as timeout or pending for retry
        status = self.queue.get_status(job_id)
        self.assertTrue(
            status["status"] in [JobStatus.TIMEOUT.value, JobStatus.PENDING.value],
            f"Expected job status to be timeout or pending, but got {status['status']}"
        )