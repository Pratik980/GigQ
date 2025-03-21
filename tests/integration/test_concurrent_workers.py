"""Tests for concurrent worker operation."""
import time
import threading
import tempfile
import os
import sqlite3
from gigq import Job, JobStatus, Worker
from tests.integration.base import IntegrationTestBase
from tests.job_functions import work_counter_job

class TestConcurrentWorkers(IntegrationTestBase):
    """Test multiple workers processing jobs concurrently."""
    
    def test_multiple_workers_job_processing(self):
        # Create more workers
        self.workers = [
            Worker(self.db_path, worker_id=f"worker-{i}", polling_interval=0.1)
            for i in range(3)
        ]
        self.worker_threads = []
        
        # Create a shared counter using SQLite for proper cross-thread tracking
        _, tracker_db_path = tempfile.mkstemp(suffix='.db')
        os.close(_)  # Close the file descriptor
        
        # Register for cleanup
        self.addCleanup(lambda: os.path.exists(tracker_db_path) and os.unlink(tracker_db_path))
        
        # Create the counter table
        conn = sqlite3.connect(tracker_db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS counter (job_id TEXT PRIMARY KEY, count INTEGER)")
        conn.commit()
        conn.close()
        
        # Submit 10 jobs using the SQLite database for counting
        job_ids = []
        for i in range(10):
            job = Job(
                name=f"job_{i}", 
                function=work_counter_job, 
                params={"job_id": f"job_{i}", "counter_db": tracker_db_path}
            )
            job_id = self.queue.submit(job)
            job_ids.append(job_id)
        
        # Start multiple workers
        def worker_func(worker):
            for _ in range(5):  # Each worker tries to process up to 5 jobs
                worker.process_one()
                time.sleep(0.05)
        
        for worker in self.workers:
            thread = threading.Thread(target=worker_func, args=(worker,))
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
        
        # Wait for all workers to finish
        for thread in self.worker_threads:
            thread.join(timeout=5)
        
        # Check the counter in the SQLite database
        conn = sqlite3.connect(tracker_db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM counter")
        processed_count = cursor.fetchone()[0]
        conn.close()
        
        # Verify the correct number of jobs were processed
        self.assertEqual(processed_count, 10)
        
        # Verify each job was processed exactly once
        for job_id in job_ids:
            status = self.queue.get_status(job_id)
            self.assertEqual(status["status"], JobStatus.COMPLETED.value)