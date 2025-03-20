"""Tests for job timeout handling."""
import time
from gigq import Job, JobStatus, Worker
from tests.integration.base import IntegrationTestBase
from tests.job_functions import sleep_job

class TestTimeoutHandling(IntegrationTestBase):
    """Test timeout handling for long-running jobs."""
    
    def test_job_timeout_detection(self):
        # Create a job with a short timeout
        job = Job(
            name="timeout_job",
            function=sleep_job,
            params={"duration": 2},  # Sleep for 2 seconds
            timeout=1,  # 1 second timeout
            max_attempts=2
        )
        
        # Submit the job
        job_id = self.queue.submit(job)
        
        # Start processing the job
        self.worker.process_one()
        
        # Sleep longer than the timeout
        time.sleep(1.5)
        
        # Have another worker check for timeouts
        another_worker = Worker(self.db_path)
        another_worker._check_for_timeouts()
        
        # Check job status
        status = self.queue.get_status(job_id)
        self.assertTrue(
            status["status"] in [JobStatus.TIMEOUT.value, JobStatus.PENDING.value]
        )