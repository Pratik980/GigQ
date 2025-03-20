"""Tests for database persistence across restarts."""
import os
import tempfile
import unittest
from gigq import Job, JobQueue, JobStatus, Worker
from tests.job_functions import simple_job

class TestDatabasePersistence(unittest.TestCase):
    """Test database persistence across restarts."""
    
    def setUp(self):
        # Create a temporary but persistent database file
        _, self.db_path = tempfile.mkstemp()
        os.unlink(self.db_path)  # Remove the file so JobQueue can create it
    
    def tearDown(self):
        # Clean up
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_job_state_persistence(self):
        # First session: Submit the job
        queue1 = JobQueue(self.db_path)
        job = Job(
            name="persistent_job", 
            function=simple_job, 
            params={"value": 42}
        )
        job_id = queue1.submit(job)
        
        # Verify job is in the database
        status1 = queue1.get_status(job_id)
        self.assertEqual(status1["status"], JobStatus.PENDING.value)
        
        # Second session: Connect to the same database and process the job
        queue2 = JobQueue(self.db_path, initialize=False)
        worker = Worker(self.db_path)
        worker.process_one()
        
        # Verify job was processed
        status2 = queue2.get_status(job_id)
        self.assertEqual(status2["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status2["result"]["result"], 84)  # 42 * 2