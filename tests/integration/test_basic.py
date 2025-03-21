"""Tests for basic job submission and processing."""

import time
from gigq import Job, JobStatus
from tests.integration.base import IntegrationTestBase
from tests.job_functions import simple_job


class TestBasic(IntegrationTestBase):
    """Test basic job submission and processing."""

    def test_simple_job(self):
        # Create and submit job
        job = Job(name="test_job", function=simple_job, params={"value": 42})
        job_id = self.queue.submit(job)

        # Process the job
        self.worker.process_one()

        # Check the result
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status["result"]["result"], 84)  # 42 * 2
