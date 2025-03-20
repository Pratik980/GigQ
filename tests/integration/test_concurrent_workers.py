"""Tests for concurrent worker operation."""
import time
import threading
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
        
        # Create a shared counter dictionary
        counter_dict = {}
        
        # Submit 10 jobs
        job_ids = []
        for i in range(10):
            job = Job(
                name=f"job_{i}", 
                function=work_counter_job, 
                params={"job_id": i, "counter_dict": counter_dict}
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
        
        # Verify all jobs were processed
        self.assertEqual(sum(counter_dict.values()), 10)
        
        # Verify each job was processed exactly once
        for job_id in job_ids:
            status = self.queue.get_status(job_id)
            self.assertEqual(status["status"], JobStatus.COMPLETED.value)