"""Tests for workflows with job dependencies."""
import time
from gigq import Job, JobStatus, Workflow
from tests.integration.base import IntegrationTestBase
from tests.job_functions import track_execution_job

class TestWorkflowDependencies(IntegrationTestBase):
    """Test workflows with dependencies between jobs."""
    
    def test_dependent_jobs_execution_order(self):
        # Create a shared tracker list to monitor execution order
        execution_tracker = []
        
        # Create a workflow
        workflow = Workflow("test_workflow")
        
        # Define jobs
        job1 = Job(
            name="job1", 
            function=track_execution_job, 
            params={"tracker": execution_tracker, "job_id": "job1"}
        )
        
        job2 = Job(
            name="job2", 
            function=track_execution_job, 
            params={"tracker": execution_tracker, "job_id": "job2"}
        )
        
        job3 = Job(
            name="job3", 
            function=track_execution_job, 
            params={"tracker": execution_tracker, "job_id": "job3"}
        )
        
        # Add jobs with dependencies
        workflow.add_job(job1)
        workflow.add_job(job2, depends_on=[job1])
        workflow.add_job(job3, depends_on=[job2])
        
        # Submit the workflow
        job_ids = workflow.submit_all(self.queue)
        
        # Start the worker
        self.start_worker()
        
        # Wait for all jobs to complete
        timeout = time.time() + 10  # 10-second timeout
        while time.time() < timeout:
            statuses = [self.queue.get_status(job_id)["status"] for job_id in job_ids]
            if all(status == JobStatus.COMPLETED.value for status in statuses):
                break
            time.sleep(0.1)
        
        # Verify execution order
        self.assertEqual(execution_tracker, ["job1", "job2", "job3"])