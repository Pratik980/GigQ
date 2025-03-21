"""
GigQ: A lightweight job queue system with SQLite backend
"""

import json
import logging
import os
import signal
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gigq")


class JobStatus(Enum):
    """Enum representing the possible states of a job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Job:
    """
    Represents a job to be executed by the queue system.
    """

    def __init__(
        self,
        name: str,
        function: Callable,
        params: Dict[str, Any] = None,
        priority: int = 0,
        dependencies: List[str] = None,
        max_attempts: int = 3,
        timeout: int = 300,
        description: str = "",
    ):
        """
        Initialize a new job.

        Args:
            name: A name for the job.
            function: The function to execute.
            params: Parameters to pass to the function.
            priority: Job priority (higher numbers executed first).
            dependencies: List of job IDs that must complete before this job runs.
            max_attempts: Maximum number of execution attempts.
            timeout: Maximum runtime in seconds before the job is considered hung.
            description: Optional description of the job.
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.function = function
        self.params = params or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.description = description
        self.created_at = datetime.now().isoformat()


class JobQueue:
    """
    Manages a queue of jobs using SQLite as a backend.
    """

    def __init__(self, db_path: str, initialize: bool = True):
        """
        Initialize the job queue.

        Args:
            db_path: Path to the SQLite database file.
            initialize: Whether to initialize the database if it doesn't exist.
        """
        self.db_path = db_path
        if initialize:
            self._initialize_db()

    def _initialize_db(self):
        """Create the necessary database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Jobs table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            function_name TEXT NOT NULL,
            function_module TEXT NOT NULL,
            params TEXT,
            priority INTEGER DEFAULT 0,
            dependencies TEXT,
            max_attempts INTEGER DEFAULT 3,
            timeout INTEGER DEFAULT 300,
            description TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            result TEXT,
            error TEXT,
            started_at TEXT,
            completed_at TEXT,
            worker_id TEXT
        )
        """
        )

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs (priority)"
        )

        # Job executions table (for history)
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS job_executions (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
        """
        )

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection to the SQLite database with appropriate settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def submit(self, job: Job) -> str:
        """
        Submit a job to the queue.

        Args:
            job: The job to submit.

        Returns:
            The ID of the submitted job.
        """
        conn = self._get_connection()
        try:
            # Store function as module and name for later import
            function_module = job.function.__module__
            function_name = job.function.__name__

            now = datetime.now().isoformat()

            # Insert the job into the database
            with conn:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        id, name, function_name, function_module, params, priority,
                        dependencies, max_attempts, timeout, description, status,
                        created_at, updated_at, attempts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.id,
                        job.name,
                        function_name,
                        function_module,
                        json.dumps(job.params),
                        job.priority,
                        json.dumps(job.dependencies),
                        job.max_attempts,
                        job.timeout,
                        job.description,
                        JobStatus.PENDING.value,
                        job.created_at,
                        now,
                        0,
                    ),
                )

            logger.info(f"Job submitted: {job.id} ({job.name})")
            return job.id
        finally:
            conn.close()

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: The ID of the job to cancel.

        Returns:
            True if the job was cancelled, False if it couldn't be cancelled.
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
                    (
                        JobStatus.CANCELLED.value,
                        datetime.now().isoformat(),
                        job_id,
                        JobStatus.PENDING.value,
                    ),
                )

            if cursor.rowcount > 0:
                logger.info(f"Job cancelled: {job_id}")
                return True
            else:
                logger.warning(
                    f"Could not cancel job {job_id}, it may be already running or completed"
                )
                return False
        finally:
            conn.close()

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the current status of a job.

        Args:
            job_id: The ID of the job to check.

        Returns:
            A dictionary containing the job's status and related information.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job_data = cursor.fetchone()

            if not job_data:
                return {"exists": False}

            result = dict(job_data)

            # Deserialize JSON fields
            if result["params"]:
                result["params"] = json.loads(result["params"])
            if result["dependencies"]:
                result["dependencies"] = json.loads(result["dependencies"])
            if result["result"]:
                result["result"] = json.loads(result["result"])

            result["exists"] = True

            # Get execution history
            cursor = conn.execute(
                "SELECT * FROM job_executions WHERE job_id = ? ORDER BY started_at ASC",
                (job_id,),
            )
            executions = [dict(row) for row in cursor.fetchall()]
            for execution in executions:
                if execution["result"]:
                    execution["result"] = json.loads(execution["result"])

            result["executions"] = executions

            return result
        finally:
            conn.close()

    def list_jobs(
        self, status: Optional[Union[JobStatus, str]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List jobs in the queue, optionally filtered by status.

        Args:
            status: Filter jobs by this status.
            limit: Maximum number of jobs to return.

        Returns:
            A list of job dictionaries.
        """
        conn = self._get_connection()
        try:
            if status:
                if isinstance(status, JobStatus):
                    status = status.value
                cursor = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
                )

            results = []
            for row in cursor.fetchall():
                job_dict = dict(row)

                # Deserialize JSON fields
                if job_dict["params"]:
                    job_dict["params"] = json.loads(job_dict["params"])
                if job_dict["dependencies"]:
                    job_dict["dependencies"] = json.loads(job_dict["dependencies"])
                if job_dict["result"]:
                    job_dict["result"] = json.loads(job_dict["result"])

                results.append(job_dict)

            return results
        finally:
            conn.close()

    def clear_completed(self, before_timestamp: Optional[str] = None) -> int:
        """
        Clear completed jobs from the queue.

        Args:
            before_timestamp: Only clear jobs completed before this timestamp.

        Returns:
            Number of jobs cleared.
        """
        conn = self._get_connection()
        try:
            with conn:
                if before_timestamp:
                    cursor = conn.execute(
                        "DELETE FROM jobs WHERE status IN (?, ?) AND completed_at < ?",
                        (
                            JobStatus.COMPLETED.value,
                            JobStatus.CANCELLED.value,
                            before_timestamp,
                        ),
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM jobs WHERE status IN (?, ?)",
                        (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value),
                    )

                return cursor.rowcount
        finally:
            conn.close()

    def requeue_job(self, job_id: str) -> bool:
        """
        Requeue a failed job, resetting its attempts.

        Args:
            job_id: The ID of the job to requeue.

        Returns:
            True if the job was requeued, False if not.
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, attempts = 0, error = NULL, updated_at = ?
                    WHERE id = ? AND status IN (?, ?, ?)
                    """,
                    (
                        JobStatus.PENDING.value,
                        datetime.now().isoformat(),
                        job_id,
                        JobStatus.FAILED.value,
                        JobStatus.TIMEOUT.value,
                        JobStatus.CANCELLED.value,
                    ),
                )

                return cursor.rowcount > 0
        finally:
            conn.close()


class Worker:
    """
    A worker that processes jobs from the queue.
    """

    def __init__(
        self, db_path: str, worker_id: Optional[str] = None, polling_interval: int = 5
    ):
        """
        Initialize a worker.

        Args:
            db_path: Path to the SQLite database file.
            worker_id: Unique identifier for this worker (auto-generated if not provided).
            polling_interval: How often to check for new jobs, in seconds.
        """
        self.db_path = db_path
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self.polling_interval = polling_interval
        self.running = False
        self.current_job_id = None
        self.conn = None
        self.logger = logging.getLogger(f"gigq.worker.{self.worker_id}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection to the SQLite database with appropriate settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _import_function(self, module_name: str, function_name: str) -> Callable:
        """
        Dynamically import a function.

        Args:
            module_name: The name of the module containing the function.
            function_name: The name of the function to import.

        Returns:
            The imported function.
        """
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, function_name)

    def _claim_job(self) -> Optional[Dict[str, Any]]:
        """
        Attempt to claim a job from the queue.

        Returns:
            A job dictionary if a job was claimed, None otherwise.
        """
        conn = self._get_connection()
        try:
            # Ensure transaction isolation
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")

            # First, check for ready jobs with no dependencies
            cursor = conn.execute(
                """
                SELECT j.* FROM jobs j
                WHERE j.status = ?
                AND (j.dependencies IS NULL OR j.dependencies = '[]')
                ORDER BY j.priority DESC, j.created_at ASC
                LIMIT 1
                """,
                (JobStatus.PENDING.value,),
            )

            job = cursor.fetchone()

            if not job:
                # Then look for jobs with dependencies and check if they're all completed
                cursor = conn.execute(
                    "SELECT id, dependencies FROM jobs WHERE status = ? AND dependencies IS NOT NULL AND dependencies != '[]'",
                    (JobStatus.PENDING.value,),
                )

                potential_jobs = cursor.fetchall()
                for potential_job in potential_jobs:
                    dependencies = json.loads(potential_job["dependencies"])
                    if not dependencies:
                        continue

                    # Check if all dependencies are completed
                    placeholders = ",".join(["?"] * len(dependencies))
                    query = f"SELECT COUNT(*) as count FROM jobs WHERE id IN ({placeholders}) AND status != ?"
                    cursor = conn.execute(
                        query, dependencies + [JobStatus.COMPLETED.value]
                    )
                    result = cursor.fetchone()

                    if result and result["count"] == 0:
                        # All dependencies satisfied, get the full job
                        cursor = conn.execute(
                            "SELECT * FROM jobs WHERE id = ?", (potential_job["id"],)
                        )
                        job = cursor.fetchone()
                        break

            if not job:
                conn.rollback()
                return None

            job_id = job["id"]
            now = datetime.now().isoformat()

            # Update the job status to running
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, worker_id = ?, started_at = ?, updated_at = ?, attempts = attempts + 1
                WHERE id = ?
                """,
                (JobStatus.RUNNING.value, self.worker_id, now, now, job_id),
            )

            # Record execution start
            execution_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO job_executions (id, job_id, worker_id, status, started_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (execution_id, job_id, self.worker_id, JobStatus.RUNNING.value, now),
            )

            # Commit the transaction
            conn.commit()

            # Get the updated job
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job = cursor.fetchone()

            result = dict(job)

            # Deserialize JSON fields
            if result["params"]:
                result["params"] = json.loads(result["params"])
            if result["dependencies"]:
                result["dependencies"] = json.loads(result["dependencies"])

            result["execution_id"] = execution_id

            return result
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error(f"Database error when claiming job: {e}")
            return None
        finally:
            conn.close()

    def _complete_job(
        self,
        job_id: str,
        execution_id: str,
        status: JobStatus,
        result: Any = None,
        error: str = None,
    ):
        """
        Mark a job as completed or failed.

        Args:
            job_id: The ID of the job.
            execution_id: The ID of the execution.
            status: The final status of the job.
            result: The result of the job (if successful).
            error: Error message (if failed).
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            result_json = json.dumps(result) if result is not None else None

            with conn:
                # Update the job
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, updated_at = ?, completed_at = ?, 
                        result = ?, error = ?, worker_id = NULL
                    WHERE id = ?
                    """,
                    (status.value, now, now, result_json, error, job_id),
                )

                # Update the execution record
                conn.execute(
                    """
                    UPDATE job_executions
                    SET status = ?, completed_at = ?, result = ?, error = ?
                    WHERE id = ?
                    """,
                    (status.value, now, result_json, error, execution_id),
                )
        finally:
            conn.close()

    def _check_for_timeouts(self):
        """Check for jobs that have timed out and mark them accordingly."""
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    SELECT j.id, j.timeout, j.started_at, j.worker_id, j.attempts, j.max_attempts
                    FROM jobs j
                    WHERE j.status = ?
                    """,
                    (JobStatus.RUNNING.value,),
                )

                running_jobs = cursor.fetchall()
                now = datetime.now()

                for job in running_jobs:
                    if not job["started_at"]:
                        continue

                    started_at = datetime.fromisoformat(job["started_at"])
                    timeout_seconds = job["timeout"] or 300  # Default 5 minutes

                    if now - started_at > timedelta(seconds=timeout_seconds):
                        # Job has timed out
                        status = (
                            JobStatus.PENDING
                            if job["attempts"] < job["max_attempts"]
                            else JobStatus.TIMEOUT
                        )

                        self.logger.warning(
                            f"Job {job['id']} timed out after {timeout_seconds} seconds"
                        )

                        conn.execute(
                            """
                            UPDATE jobs
                            SET status = ?, updated_at = ?, worker_id = NULL,
                                error = ?
                            WHERE id = ?
                            """,
                            (
                                status.value,
                                now.isoformat(),
                                f"Job timed out after {timeout_seconds} seconds",
                                job["id"],
                            ),
                        )

                        # Also update any execution records
                        conn.execute(
                            """
                            UPDATE job_executions
                            SET status = ?, completed_at = ?, error = ?
                            WHERE job_id = ? AND status = ?
                            """,
                            (
                                JobStatus.TIMEOUT.value,
                                now.isoformat(),
                                f"Job timed out after {timeout_seconds} seconds",
                                job["id"],
                                JobStatus.RUNNING.value,
                            ),
                        )
        finally:
            conn.close()

    def process_one(self) -> bool:
        """
        Process a single job from the queue.

        Returns:
            True if a job was processed, False if no job was available.
        """
        # Check for timed out jobs first
        self._check_for_timeouts()

        # Try to claim a job
        job = self._claim_job()
        if not job:
            return False

        job_id = job["id"]
        execution_id = job["execution_id"]
        self.current_job_id = job_id

        self.logger.info(f"Processing job {job_id} ({job['name']})")

        try:
            # Load the function
            func = self._import_function(job["function_module"], job["function_name"])

            # Execute the job
            start_time = time.time()
            result = func(**job["params"])
            execution_time = time.time() - start_time

            # Record success
            self.logger.info(
                f"Job {job_id} completed successfully in {execution_time:.2f}s"
            )
            self._complete_job(job_id, execution_id, JobStatus.COMPLETED, result=result)

        except Exception as e:
            # Record failure
            self.logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

            # Check if we need to retry
            if job["attempts"] < job["max_attempts"]:
                # We'll retry
                conn = self._get_connection()
                try:
                    with conn:
                        now = datetime.now().isoformat()
                        conn.execute(
                            """
                            UPDATE jobs
                            SET status = ?, updated_at = ?, worker_id = NULL,
                                error = ?
                            WHERE id = ?
                            """,
                            (JobStatus.PENDING.value, now, str(e), job_id),
                        )

                        # Update the execution record
                        conn.execute(
                            """
                            UPDATE job_executions
                            SET status = ?, completed_at = ?, error = ?
                            WHERE id = ?
                            """,
                            (JobStatus.FAILED.value, now, str(e), execution_id),
                        )
                finally:
                    conn.close()
            else:
                # Max retries reached
                self._complete_job(job_id, execution_id, JobStatus.FAILED, error=str(e))

        finally:
            self.current_job_id = None

        return True

    def start(self):
        """Start the worker process."""
        self.running = True
        self.logger.info(f"Worker {self.worker_id} starting")

        # Set up signal handlers
        def handle_signal(sig, frame):
            self.logger.info(f"Received signal {sig}, stopping worker")
            self.running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        try:
            while self.running:
                # Process one job
                job_processed = self.process_one()

                # If no job was available, wait before checking again
                if not job_processed:
                    time.sleep(self.polling_interval)
        finally:
            self.logger.info(f"Worker {self.worker_id} stopped")

    def stop(self):
        """Stop the worker process."""
        self.running = False
        self.logger.info(f"Worker {self.worker_id} stopping")


class Workflow:
    """
    A utility class to help define workflows of dependent jobs.
    """

    def __init__(self, name: str):
        """
        Initialize a new workflow.

        Args:
            name: Name of the workflow.
        """
        self.name = name
        self.jobs = []
        self.job_map = {}

    def add_job(self, job: Job, depends_on: List[Job] = None) -> Job:
        """
        Add a job to the workflow, with optional dependencies.

        Args:
            job: The job to add.
            depends_on: List of jobs this job depends on.

        Returns:
            The job that was added.
        """
        if depends_on:
            job.dependencies = [j.id for j in depends_on]

        self.jobs.append(job)
        self.job_map[job.id] = job
        return job

    def submit_all(self, queue: JobQueue) -> List[str]:
        """
        Submit all jobs in the workflow to a queue.

        Args:
            queue: The job queue to submit to.

        Returns:
            List of job IDs that were submitted.
        """
        job_ids = []
        for job in self.jobs:
            job_id = queue.submit(job)
            job_ids.append(job_id)
        return job_ids
