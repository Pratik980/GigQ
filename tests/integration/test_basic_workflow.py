"""Tests for basic job submission and processing."""
import time
from gigq import Job, JobStatus
from tests.integration.base import IntegrationTestBase
from tests.job_functions import simple_job

class TestBasicWorkflow(IntegrationTestBase):
    """Test a basic workflow from job submission to completion."""
    
    def test_job_submission_and_processing(self):
        job = Job(name="test_job", function=simple_job, params={"value": 42})
        
        # Submit the job
        job_id = self.queue.submit(job)
        
        # Start the worker
        self.start_worker()
        
        # Poll until the job completes or times out
        timeout = time.time() + 5  # 5-second timeout
        while time.time() < timeout:
            status = self.queue.get_status(job_id)
            if status["status"] == JobStatus.COMPLETED.value:
                break
            time.sleep(0.1)
        
        # Verify the job completed successfully
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status["result"]["result"], 84)  # 42 * 2