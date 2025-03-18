"""
Tests for the GigQ library
"""
import os
import sqlite3
import tempfile
import time
import uuid
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from gigq import Job, JobQueue, Worker, JobStatus, Workflow


def example_job_function(value=0):
    """Example job function for testing."""
    return {"result": value * 2}


def failing_job_function():
    """Example job function that fails."""
    raise ValueError("This job is designed to fail")


class TestJob(unittest.TestCase):
    """Tests for the Job class."""
    
    def test_job_initialization(self):
        """Test that a job can be initialized with the correct parameters."""
        job = Job(
            name="test_job",
            function=example_job_function,
            params={"value": 42},
            priority=5,
            dependencies=["job1", "job2"],
            max_attempts=2,
            timeout=120,
            description="A test job"
        )
        
        self.assertEqual(job.name, "test_job")
        self.assertEqual(job.function, example_job_function)
        self.assertEqual(job.params, {"value": 42})
        self.assertEqual(job.priority, 5)
        self.assertEqual(job.dependencies, ["job1", "job2"])
        self.assertEqual(job.max_attempts, 2)
        self.assertEqual(job.timeout, 120)
        self.assertEqual(job.description, "A test job")
        self.assertTrue(job.id)  # ID should be generated


class TestJobQueue(unittest.TestCase):
    """Tests for the JobQueue class."""
    
    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.queue = JobQueue(self.db_path)
    
    def tearDown(self):
        """Clean up the temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_submit_job(self):
        """Test that a job can be submitted to the queue."""
        job = Job(
            name="test_job",
            function=example_job_function,
            params={"value": 42}
        )
        
        job_id = self.queue.submit(job)
        self.assertEqual(job_id, job.id)
        
        # Check that the job was stored correctly
        status = self.queue.get_status(job_id)
        self.assertTrue(status["exists"])
        self.assertEqual(status["name"], "test_job")
        self.assertEqual(status["status"], JobStatus.PENDING.value)
    
    def test_cancel_job(self):
        """Test that a pending job can be cancelled."""
        job = Job(
            name="test_job",
            function=example_job_function
        )
        
        job_id = self.queue.submit(job)
        self.assertTrue(self.queue.cancel(job_id))
        
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.CANCELLED.value)
    
    def test_list_jobs(self):
        """Test that jobs can be listed from the queue."""
        # Submit some jobs
        jobs = []
        for i in range(5):
            job = Job(
                name=f"test_job_{i}",
                function=example_job_function,
                params={"value": i}
            )
            job_id = self.queue.submit(job)
            jobs.append(job_id)
        
        # List all jobs
        job_list = self.queue.list_jobs()
        self.assertEqual(len(job_list), 5)
        
        # Cancel one job
        self.queue.cancel(jobs[0])
        
        # List only pending jobs
        pending_jobs = self.queue.list_jobs(status=JobStatus.PENDING)
        self.assertEqual(len(pending_jobs), 4)
        
        # List only cancelled jobs
        cancelled_jobs = self.queue.list_jobs(status=JobStatus.CANCELLED)
        self.assertEqual(len(cancelled_jobs), 1)
    
    def test_requeue_job(self):
        """Test that a failed job can be requeued."""
        job = Job(
            name="failing_job",
            function=failing_job_function,
            max_attempts=1
        )
        
        job_id = self.queue.submit(job)
        
        # Mark job as failed
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
            (JobStatus.FAILED.value, "Test error", job_id)
        )
        conn.commit()
        conn.close()
        
        # Verify job is failed
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.FAILED.value)
        
        # Requeue the job
        self.assertTrue(self.queue.requeue_job(job_id))
        
        # Verify job is pending again
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.PENDING.value)
        self.assertEqual(status["attempts"], 0)  # Attempts should be reset


class TestWorker(unittest.TestCase):
    """Tests for the Worker class."""
    
    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.queue = JobQueue(self.db_path)
    
    def tearDown(self):
        """Clean up the temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_process_one_job(self):
        """Test that a worker can process a job."""
        job = Job(
            name="test_job",
            function=example_job_function,
            params={"value": 42}
        )
        
        job_id = self.queue.submit(job)
        
        worker = Worker(self.db_path)
        self.assertTrue(worker.process_one())
        
        # Check that the job was processed correctly
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status["result"]["result"], 84)  # 42 * 2
    
    def test_process_failing_job(self):
        """Test that a worker handles failing jobs correctly."""
        job = Job(
            name="failing_job",
            function=failing_job_function,
            max_attempts=2
        )
        
        job_id = self.queue.submit(job)
        
        worker = Worker(self.db_path)
        
        # First attempt should fail but job should be requeued
        self.assertTrue(worker.process_one())
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.PENDING.value)
        self.assertEqual(status["attempts"], 1)
        
        # Second attempt should fail and job should be marked as failed
        self.assertTrue(worker.process_one())
        status = self.queue.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.FAILED.value)
        self.assertEqual(status["attempts"], 2)
        self.assertIn("This job is designed to fail", status["error"])
    
    def test_timeout_detection(self):
        """Test that the worker detects timed out jobs."""
        
        # Instead of trying to import a function, let's use a direct approach with monkeypatching
        conn = sqlite3.connect(self.db_path)
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # Insert a fake "running" job that started an hour ago (so it's definitely timed out)
        with conn:
            # Insert job record
            conn.execute(
                """
                INSERT INTO jobs (
                    id, name, function_name, function_module, params, 
                    status, created_at, updated_at, started_at,
                    timeout, worker_id, attempts, max_attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, "test_timeout_job", "dummy_function", "dummy_module",
                    "{}", JobStatus.RUNNING.value, now, now, one_hour_ago,
                    10, "test-worker", 1, 3
                )
            )
            
            # Insert execution record
            conn.execute(
                """
                INSERT INTO job_executions (
                    id, job_id, worker_id, status, started_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), job_id, "test-worker", JobStatus.RUNNING.value, one_hour_ago
                )
            )
        
        conn.close()
        
        # Now check for timeouts
        worker = Worker(self.db_path)
        worker._check_for_timeouts()
        
        # Get the updated job status
        status = self.queue.get_status(job_id)
        
        # The job should be marked as timed out or re-queued
        self.assertIn(status["status"], [JobStatus.PENDING.value, JobStatus.TIMEOUT.value])
        self.assertIn("timed out", status.get("error", ""))


class TestWorkflow(unittest.TestCase):
    """Tests for the Workflow class."""
    
    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.queue = JobQueue(self.db_path)
    
    def tearDown(self):
        """Clean up the temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_workflow_dependencies(self):
        """Test that workflow dependencies are set correctly."""
        workflow = Workflow("test_workflow")
        
        job1 = Job(name="job1", function=example_job_function)
        job2 = Job(name="job2", function=example_job_function)
        job3 = Job(name="job3", function=example_job_function)
        
        workflow.add_job(job1)
        workflow.add_job(job2, depends_on=[job1])
        workflow.add_job(job3, depends_on=[job1, job2])
        
        self.assertEqual(len(job1.dependencies), 0)
        self.assertEqual(len(job2.dependencies), 1)
        self.assertEqual(len(job3.dependencies), 2)
        self.assertEqual(job2.dependencies[0], job1.id)
        self.assertTrue(job1.id in job3.dependencies)
        self.assertTrue(job2.id in job3.dependencies)
    
    def test_workflow_submission(self):
        """Test that a workflow can be submitted."""
        workflow = Workflow("test_workflow")
        
        job1 = Job(name="job1", function=example_job_function)
        job2 = Job(name="job2", function=example_job_function, params={"value": 1})
        job3 = Job(name="job3", function=example_job_function, params={"value": 2})
        
        workflow.add_job(job1)
        workflow.add_job(job2, depends_on=[job1])
        workflow.add_job(job3, depends_on=[job2])
        
        job_ids = workflow.submit_all(self.queue)
        
        self.assertEqual(len(job_ids), 3)
        
        # Check that all jobs are in the queue
        for job_id in job_ids:
            status = self.queue.get_status(job_id)
            self.assertTrue(status["exists"])
            self.assertEqual(status["status"], JobStatus.PENDING.value)
        
        # Process first job
        worker = Worker(self.db_path)
        worker.process_one()
        
        # Check that first job is completed
        status = self.queue.get_status(job_ids[0])
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        
        # Process second job
        worker.process_one()
        
        # Check that second job is completed
        status = self.queue.get_status(job_ids[1])
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        
        # Process third job
        worker.process_one()
        
        # Check that third job is completed
        status = self.queue.get_status(job_ids[2])
        self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        self.assertEqual(status["result"]["result"], 4)  # 2 * 2
    
    def test_concurrent_workers(self):
        """Test that multiple workers can process jobs from the same queue."""
        # Submit 10 jobs
        job_ids = []
        for i in range(10):
            job = Job(
                name=f"concurrent_job_{i}",
                function=example_job_function,
                params={"value": i}
            )
            job_id = self.queue.submit(job)
            job_ids.append(job_id)
        
        # Create two workers
        worker1 = Worker(self.db_path, worker_id="worker1")
        worker2 = Worker(self.db_path, worker_id="worker2")
        
        # Process 5 jobs with each worker
        for _ in range(5):
            worker1.process_one()
            worker2.process_one()
        
        # Check that all jobs are completed
        for job_id in job_ids:
            status = self.queue.get_status(job_id)
            self.assertEqual(status["status"], JobStatus.COMPLETED.value)
        
        # Check that some jobs were processed by each worker
        worker1_jobs = 0
        worker2_jobs = 0
        
        for job_id in job_ids:
            status = self.queue.get_status(job_id)
            for execution in status["executions"]:
                if execution["worker_id"] == "worker1":
                    worker1_jobs += 1
                elif execution["worker_id"] == "worker2":
                    worker2_jobs += 1
        
        self.assertGreater(worker1_jobs, 0)
        self.assertGreater(worker2_jobs, 0)
        self.assertEqual(worker1_jobs + worker2_jobs, 10)


if __name__ == "__main__":
    unittest.main()
