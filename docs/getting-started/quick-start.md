# Quick Start

This guide will help you quickly get started with GigQ by walking through the core features.

## Basic Job Processing

Let's start with a simple example of defining, submitting, and processing a job.

### 1. Define a Job Function

First, define a function that will be executed as a job:

```python
def process_file(filename, threshold=0.5):
    """Process a file with the given threshold."""
    with open(filename, 'r') as f:
        content = f.read()

    # Do some processing
    word_count = len(content.split())

    # Return some results
    return {
        "filename": filename,
        "word_count": word_count,
        "threshold_applied": threshold,
        "processed": True
    }
```

### 2. Create and Submit a Job

Now, let's create a job and submit it to the queue:

```python
from gigq import Job, JobQueue

# Create a job queue (or connect to an existing one)
queue = JobQueue("my_jobs.db")

# Create a job
job = Job(
    name="process_csv_file",
    function=process_file,
    params={"filename": "data.csv", "threshold": 0.7},
    max_attempts=3,    # Retry up to 3 times on failure
    timeout=300        # Timeout after 5 minutes
)

# Submit the job
job_id = queue.submit(job)
print(f"Submitted job with ID: {job_id}")
```

### 3. Start a Worker to Process Jobs

You can start a worker to process jobs in the queue:

```python
from gigq import Worker

# Create a worker
worker = Worker("my_jobs.db")

# Start the worker (this will block until stopped)
worker.start()
```

Alternatively, you can process a single job:

```python
# Process just one job
worker.process_one()
```

### 4. Check Job Status

You can check the status of a job:

```python
# Get the status of a job
status = queue.get_status(job_id)
print(f"Job status: {status['status']}")

# If the job is completed, you can access the result
if status["status"] == "completed":
    print(f"Result: {status['result']}")
```

## Using the Command Line Interface

GigQ provides a command-line interface for working with jobs.

### Submit a Job

```bash
gigq --db my_jobs.db submit my_module.process_file --name "Process CSV" --param "filename=data.csv" --param "threshold=0.7"
```

### Start a Worker

```bash
# Start a worker
gigq --db my_jobs.db worker

# Process just one job
gigq --db my_jobs.db worker --once
```

### Check Job Status

```bash
gigq --db my_jobs.db status your-job-id --show-result
```

### List Jobs

```bash
gigq --db my_jobs.db list
gigq --db my_jobs.db list --status pending
```

### Cancel a Job

```bash
gigq --db my_jobs.db cancel your-job-id
```

## Creating Workflows

GigQ allows you to create workflows with dependent jobs:

```python
from gigq import Workflow

# Create a workflow
workflow = Workflow("data_processing")

# Define jobs
download_job = Job(
    name="download",
    function=download_data,
    params={"url": "https://example.com/data.csv"}
)

process_job = Job(
    name="process",
    function=process_file,
    params={"filename": "data.csv"}
)

analyze_job = Job(
    name="analyze",
    function=analyze_data,
    params={"processed_file": "processed.csv"}
)

# Add jobs to workflow with dependencies
workflow.add_job(download_job)
workflow.add_job(process_job, depends_on=[download_job])
workflow.add_job(analyze_job, depends_on=[process_job])

# Submit all jobs in the workflow
job_ids = workflow.submit_all(queue)
```

## Next Steps

Now that you understand the basics of GigQ, you can:

- Learn more about [job definition and parameters](../user-guide/defining-jobs.md)
- Explore advanced [workflow capabilities](../user-guide/workflows.md)
- See a complete [example application](../examples/github-archive.md)
- Understand [how GigQ handles errors](../user-guide/error-handling.md)
