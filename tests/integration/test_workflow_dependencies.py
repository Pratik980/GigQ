"""Tests for workflows with job dependencies."""
import os
import tempfile
import time
import sqlite3
from gigq import Job, JobStatus, Workflow
from tests.integration.base import IntegrationTestBase
from tests.job_functions import track_execution_job

class TestWorkflowDependencies(IntegrationTestBase):
    """Test workflows with dependencies between jobs."""
    
    def test_dependent_jobs_execution_order(self):
        # Create a shared list to track execution order
        # Note: We can't pass this directly to jobs as it won't be shared properly
        execution_tracker = []
        
        # Create a separate SQLite database for tracking execution order
        _, tracker_db_path = tempfile.mkstemp(suffix='.db')
        os.close(_)  # Close the file descriptor
        
        # Register for cleanup
        self.addCleanup(lambda: os.path.exists(tracker_db_path) and os.unlink(tracker_db_path))
        
        # Create the tracking table
        conn = sqlite3.connect(tracker_db_path)
        conn.execute("CREATE TABLE execution_order (id INTEGER PRIMARY KEY, job_id TEXT)")
        conn.commit()
        conn.close()
        
        # Create a workflow
        workflow = Workflow("test_workflow")
        
        # Define jobs using the imported track_execution_job function
        job1 = Job(
            name="job1", 
            function=track_execution_job, 
            params={"job_id": "job1", "tracker_file": tracker_db_path}
        )
        
        job2 = Job(
            name="job2", 
            function=track_execution_job, 
            params={"job_id": "job2", "tracker_file": tracker_db_path}
        )
        
        job3 = Job(
            name="job3", 
            function=track_execution_job, 
            params={"job_id": "job3", "tracker_file": tracker_db_path}
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
        
        # Stop the worker
        self.stop_worker()
        
        # Read the execution order from the database
        conn = sqlite3.connect(tracker_db_path)
        cursor = conn.execute("SELECT job_id FROM execution_order ORDER BY id")
        execution_order = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Verify execution order
        self.assertEqual(execution_order, ["job1", "job2", "job3"])