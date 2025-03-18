# Custom Job Types

This page explains how to extend GigQ with custom job types to meet specific requirements and use cases.

## Introduction to Custom Job Types

While GigQ's standard `Job` class handles most scenarios, you may need specialized job behavior for particular use cases. Custom job types allow you to:

1. Encapsulate domain-specific job behavior
2. Add custom validation and error handling
3. Implement specialized execution logic
4. Provide convenient interfaces for specific job patterns

## Creating a Basic Custom Job Type

To create a custom job type, subclass the `Job` class:

```python
from gigq import Job

class DataProcessingJob(Job):
    """A specialized job for data processing tasks."""

    def __init__(self, name, input_file, output_file, **kwargs):
        """
        Initialize a data processing job.

        Args:
            name: Name of the job
            input_file: Path to the input file
            output_file: Path to the output file
            **kwargs: Additional arguments for the base Job class
        """
        # Define the job function
        def process_data(input_file, output_file):
            # Data processing logic
            print(f"Processing {input_file} to {output_file}")
            # ... processing code ...
            return {
                "input": input_file,
                "output": output_file,
                "success": True
            }

        # Set up job parameters
        params = {
            "input_file": input_file,
            "output_file": output_file
        }

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=process_data,
            params=params,
            **kwargs
        )

        # Store additional attributes
        self.input_file = input_file
        self.output_file = output_file
```

Usage:

```python
# Create and submit a data processing job
job = DataProcessingJob(
    name="process_csv",
    input_file="data.csv",
    output_file="processed.csv",
    priority=10,
    max_attempts=3
)

queue = JobQueue("jobs.db")
job_id = queue.submit(job)
```

## Adding Custom Validation

Custom job types can include validation logic:

```python
import os
from gigq import Job

class FileConversionJob(Job):
    """Job for converting files from one format to another."""

    SUPPORTED_FORMATS = {
        'csv': ['.xlsx', '.json'],
        'json': ['.csv', '.xml'],
        'xlsx': ['.csv'],
        'xml': ['.json']
    }

    def __init__(self, name, source_file, target_format, **kwargs):
        """
        Initialize a file conversion job.

        Args:
            name: Name of the job
            source_file: Path to the source file
            target_format: Target format (without the dot)
            **kwargs: Additional arguments for the base Job class
        """
        # Validate inputs
        self._validate_inputs(source_file, target_format)

        # Determine output file path
        source_base, source_ext = os.path.splitext(source_file)
        target_file = f"{source_base}.{target_format}"

        # Define the job function
        def convert_file(source_file, target_file):
            print(f"Converting {source_file} to {target_file}")
            # ... conversion code ...
            return {
                "source": source_file,
                "target": target_file
            }

        # Set up job parameters
        params = {
            "source_file": source_file,
            "target_file": target_file
        }

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=convert_file,
            params=params,
            **kwargs
        )

        # Store additional attributes
        self.source_file = source_file
        self.target_format = target_format
        self.target_file = target_file

    def _validate_inputs(self, source_file, target_format):
        """Validate input parameters."""
        # Check that source file exists
        if not os.path.exists(source_file):
            raise ValueError(f"Source file not found: {source_file}")

        # Check that source format is supported
        source_base, source_ext = os.path.splitext(source_file)
        source_format = source_ext.lstrip('.')

        if source_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported source format: {source_format}")

        # Check that target format is supported for this source format
        if target_format not in self.SUPPORTED_FORMATS[source_format]:
            raise ValueError(
                f"Cannot convert {source_format} to {target_format}. "
                f"Supported targets: {self.SUPPORTED_FORMATS[source_format]}"
            )
```

Usage:

```python
try:
    job = FileConversionJob(
        name="convert_data",
        source_file="data.csv",
        target_format="json"
    )
    queue.submit(job)
except ValueError as e:
    print(f"Validation error: {e}")
```

## Creating a Job Factory

For complex job configurations, use a factory pattern:

```python
from gigq import Job, Workflow

class ETLJobFactory:
    """Factory for creating ETL (Extract, Transform, Load) jobs."""

    def __init__(self, source_system, destination_system):
        """
        Initialize the ETL job factory.

        Args:
            source_system: Configuration for the source system
            destination_system: Configuration for the destination system
        """
        self.source_system = source_system
        self.destination_system = destination_system

    def create_extract_job(self, name, query, **kwargs):
        """Create a job to extract data from the source system."""
        def extract_data(source_system, query):
            print(f"Extracting data from {source_system['name']} with query: {query}")
            # ... extraction code ...
            return {"data": "extracted_data", "source": source_system['name']}

        return Job(
            name=name,
            function=extract_data,
            params={"source_system": self.source_system, "query": query},
            **kwargs
        )

    def create_transform_job(self, name, transformation_rules, **kwargs):
        """Create a job to transform the extracted data."""
        def transform_data(data, transformation_rules):
            print(f"Transforming data with rules: {transformation_rules}")
            # ... transformation code ...
            return {"data": "transformed_data", "rules_applied": transformation_rules}

        return Job(
            name=name,
            function=transform_data,
            params={"data": "extracted_data", "transformation_rules": transformation_rules},
            **kwargs
        )

    def create_load_job(self, name, table_name, **kwargs):
        """Create a job to load the transformed data into the destination system."""
        def load_data(destination_system, data, table_name):
            print(f"Loading data to {destination_system['name']}.{table_name}")
            # ... loading code ...
            return {
                "destination": destination_system['name'],
                "table": table_name,
                "rows_loaded": 100
            }

        return Job(
            name=name,
            function=load_data,
            params={
                "destination_system": self.destination_system,
                "data": "transformed_data",
                "table_name": table_name
            },
            **kwargs
        )

    def create_etl_workflow(self, base_name, query, transformation_rules, table_name):
        """Create a complete ETL workflow."""
        workflow = Workflow(f"etl_{base_name}")

        extract_job = self.create_extract_job(
            f"{base_name}_extract",
            query=query
        )

        transform_job = self.create_transform_job(
            f"{base_name}_transform",
            transformation_rules=transformation_rules
        )

        load_job = self.create_load_job(
            f"{base_name}_load",
            table_name=table_name
        )

        workflow.add_job(extract_job)
        workflow.add_job(transform_job, depends_on=[extract_job])
        workflow.add_job(load_job, depends_on=[transform_job])

        return workflow
```

Usage:

```python
# Create an ETL factory
etl_factory = ETLJobFactory(
    source_system={
        "name": "mysql_db",
        "connection_string": "mysql://user:pass@host/db"
    },
    destination_system={
        "name": "data_warehouse",
        "connection_string": "postgresql://user:pass@host/db"
    }
)

# Create and submit an ETL workflow
workflow = etl_factory.create_etl_workflow(
    base_name="daily_sales",
    query="SELECT * FROM sales WHERE date = CURDATE()",
    transformation_rules=["format_currency", "aggregate_by_region"],
    table_name="daily_sales_summary"
)

queue = JobQueue("etl_jobs.db")
job_ids = workflow.submit_all(queue)
```

## Advanced Job Types

### Parameterized Job

A job type that enforces specific parameters:

```python
class ParameterizedJob(Job):
    """A job that enforces specific parameter types."""

    def __init__(self, name, function, params=None, **kwargs):
        """
        Initialize a parameterized job.

        Args:
            name: Name of the job
            function: Function to execute
            params: Parameters to pass to the function
            **kwargs: Additional arguments for the base Job class
        """
        # Get the function's signature
        import inspect
        self.signature = inspect.signature(function)

        # Validate parameters against function signature
        params = params or {}
        self._validate_params(params)

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=function,
            params=params,
            **kwargs
        )

    def _validate_params(self, params):
        """Validate parameters against the function signature."""
        # Check required parameters
        for name, param in self.signature.parameters.items():
            if param.default == inspect.Parameter.empty and name not in params:
                raise ValueError(f"Missing required parameter: {name}")

        # Check for unexpected parameters
        for name in params:
            if name not in self.signature.parameters:
                raise ValueError(f"Unexpected parameter: {name}")
```

### Periodic Job

A job type designed for recurring execution:

```python
class PeriodicJob(Job):
    """A job designed to run periodically."""

    def __init__(self, name, function, interval, **kwargs):
        """
        Initialize a periodic job.

        Args:
            name: Name of the job
            function: Function to execute
            interval: Interval in seconds between runs
            **kwargs: Additional arguments for the base Job class
        """
        params = kwargs.pop('params', {})

        # Add metadata about the schedule
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            'periodic': True,
            'interval': interval,
            'last_run': None,
            'next_run': None
        })

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=function,
            params=params,
            metadata=metadata,
            **kwargs
        )

        self.interval = interval

    def reschedule(self, queue):
        """
        Reschedule this job after execution.

        Args:
            queue: JobQueue to resubmit to

        Returns:
            ID of the new job
        """
        import time
        now = time.time()

        # Create a new instance with updated schedule
        new_job = self.__class__(
            name=self.name,
            function=self.function,
            interval=self.interval,
            params=self.params,
            priority=self.priority,
            max_attempts=self.max_attempts,
            timeout=self.timeout,
            description=self.description
        )

        # Update schedule metadata
        new_job.metadata = self.metadata.copy()
        new_job.metadata['last_run'] = now
        new_job.metadata['next_run'] = now + self.interval

        # Submit the new job
        return queue.submit(new_job)
```

### Retry Strategies

A job type with custom retry strategies:

```python
import random
import time
from gigq import Job

class RetryStrategyJob(Job):
    """A job with customizable retry strategies."""

    # Retry strategies
    RETRY_FIXED = "fixed"
    RETRY_EXPONENTIAL = "exponential"
    RETRY_RANDOM = "random"

    def __init__(self, name, function, retry_strategy="fixed", retry_params=None, **kwargs):
        """
        Initialize a job with custom retry strategy.

        Args:
            name: Name of the job
            function: Function to execute
            retry_strategy: Strategy for retries (fixed, exponential, random)
            retry_params: Parameters for the retry strategy
            **kwargs: Additional arguments for the base Job class
        """
        self.retry_strategy = retry_strategy
        self.retry_params = retry_params or {}

        # Wrap the function to handle retries
        wrapped_function = self._wrap_function_with_retries(function)

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=wrapped_function,
            **kwargs
        )

    def _wrap_function_with_retries(self, function):
        """Wrap the function with retry logic."""
        def wrapped_function(*args, **kwargs):
            max_retries = self.retry_params.get("max_retries", 3)
            attempt = 0

            while attempt <= max_retries:
                try:
                    return function(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt > max_retries:
                        raise

                    # Calculate delay based on strategy
                    delay = self._calculate_retry_delay(attempt)

                    # Log the retry
                    print(f"Retry {attempt}/{max_retries} after {delay:.2f}s: {str(e)}")

                    # Wait before retry
                    time.sleep(delay)

        return wrapped_function

    def _calculate_retry_delay(self, attempt):
        """Calculate the delay before the next retry."""
        base_delay = self.retry_params.get("base_delay", 1.0)
        max_delay = self.retry_params.get("max_delay", 60.0)

        if self.retry_strategy == self.RETRY_FIXED:
            delay = base_delay

        elif self.retry_strategy == self.RETRY_EXPONENTIAL:
            # Exponential backoff: base_delay * 2^attempt
            delay = base_delay * (2 ** (attempt - 1))

        elif self.retry_strategy == self.RETRY_RANDOM:
            # Random delay between base_delay and base_delay * 3
            delay = base_delay + (random.random() * base_delay * 2)

        else:
            delay = base_delay

        # Cap at max_delay
        return min(delay, max_delay)
```

Usage:

```python
def unstable_api_call(url):
    """Simulate an unstable API that sometimes fails."""
    import random
    if random.random() < 0.7:  # 70% chance of failure
        raise ConnectionError("API connection failed")
    return {"status": "success", "data": "some data"}

# Create a job with exponential backoff
job = RetryStrategyJob(
    name="api_call",
    function=unstable_api_call,
    retry_strategy=RetryStrategyJob.RETRY_EXPONENTIAL,
    retry_params={
        "max_retries": 5,
        "base_delay": 1.0,
        "max_delay": 30.0
    },
    params={"url": "https://api.example.com/data"}
)

queue.submit(job)
```

## Job Type with Custom Worker Handling

You can create job types that require custom worker behavior:

```python
class PrioritizedJob(Job):
    """A job with advanced priority handling."""

    def __init__(self, name, function, priority_category="normal", **kwargs):
        """
        Initialize a job with category-based priority.

        Args:
            name: Name of the job
            function: Function to execute
            priority_category: Category for priority (critical, high, normal, low, background)
            **kwargs: Additional arguments for the base Job class
        """
        # Map categories to numeric priorities
        priority_map = {
            "critical": 100,
            "high": 50,
            "normal": 0,
            "low": -50,
            "background": -100
        }

        # Get numeric priority
        if priority_category not in priority_map:
            raise ValueError(f"Invalid priority category: {priority_category}")

        numeric_priority = priority_map[priority_category]

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=function,
            priority=numeric_priority,
            **kwargs
        )

        self.priority_category = priority_category
```

Then create a custom worker that knows how to handle these jobs:

```python
class PrioritizedWorker(Worker):
    """A worker that respects priority categories."""

    def __init__(self, db_path, allowed_categories=None, **kwargs):
        """
        Initialize a prioritized worker.

        Args:
            db_path: Path to the SQLite database file
            allowed_categories: List of priority categories this worker can process
            **kwargs: Additional arguments for the base Worker class
        """
        super().__init__(db_path, **kwargs)
        self.allowed_categories = allowed_categories or ["critical", "high", "normal", "low", "background"]

    def _claim_job(self):
        """Claim a job from the queue, respecting priority categories."""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")

            # Map allowed categories to priority ranges
            priority_ranges = []
            if "critical" in self.allowed_categories:
                priority_ranges.append("priority >= 100")
            if "high" in self.allowed_categories:
                priority_ranges.append("(priority >= 50 AND priority < 100)")
            if "normal" in self.allowed_categories:
                priority_ranges.append("(priority >= -50 AND priority < 50)")
            if "low" in self.allowed_categories:
                priority_ranges.append("(priority >= -100 AND priority < -50)")
            if "background" in self.allowed_categories:
                priority_ranges.append("priority < -100")

            # Build the query
            priority_clause = " OR ".join(priority_ranges)
            query = f"""
            SELECT * FROM jobs
            WHERE status = ? AND ({priority_clause})
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """

            cursor = conn.execute(query, (JobStatus.PENDING.value,))

            # Continue with normal job claiming process
            # ...
```

Usage:

```python
# Create prioritized jobs
critical_job = PrioritizedJob(
    name="critical_task",
    function=critical_function,
    priority_category="critical"
)

normal_job = PrioritizedJob(
    name="normal_task",
    function=normal_function,
    priority_category="normal"
)

background_job = PrioritizedJob(
    name="background_task",
    function=background_function,
    priority_category="background"
)

# Create specialized workers
critical_worker = PrioritizedWorker(
    "jobs.db",
    allowed_categories=["critical", "high"]
)

background_worker = PrioritizedWorker(
    "jobs.db",
    allowed_categories=["low", "background"]
)
```

## Integrating with External Task Systems

You can create job types that integrate with external task systems:

```python
class CeleryIntegrationJob(Job):
    """A job that delegates to Celery for execution."""

    def __init__(self, name, celery_task, task_args=None, task_kwargs=None, **kwargs):
        """
        Initialize a job that delegates to Celery.

        Args:
            name: Name of the job
            celery_task: Celery task function
            task_args: Positional arguments for the Celery task
            task_kwargs: Keyword arguments for the Celery task
            **kwargs: Additional arguments for the base Job class
        """
        self.celery_task = celery_task
        self.task_args = task_args or []
        self.task_kwargs = task_kwargs or {}

        # Define the job function that delegates to Celery
        def run_celery_task(task_name, task_args, task_kwargs):
            # Import celery here to avoid making it a dependency for all of GigQ
            import importlib
            module_name, task_name = task_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            task = getattr(module, task_name)

            # Send the task to Celery and wait for result
            result = task.delay(*task_args, **task_kwargs)
            return {"celery_task_id": result.id, "result": result.get()}

        # Initialize the base Job class
        super().__init__(
            name=name,
            function=run_celery_task,
            params={
                "task_name": f"{celery_task.__module__}.{celery_task.__name__}",
                "task_args": self.task_args,
                "task_kwargs": self.task_kwargs
            },
            **kwargs
        )
```

## Performance Considerations

When creating custom job types, keep these performance considerations in mind:

1. **Serialization**: All job parameters must be JSON-serializable
2. **Function Imports**: Functions must be importable from their module
3. **Memory Usage**: Avoid storing large data in job attributes
4. **CPU Usage**: Complex validation logic can slow down job submission

## Best Practices

1. **Clear Naming**: Give your custom job types clear, descriptive names
2. **Modular Design**: Break complex jobs into smaller, more manageable ones
3. **Good Documentation**: Document your custom job types thoroughly
4. **Validation**: Add input validation to prevent errors during execution
5. **Error Handling**: Implement appropriate error handling strategies
6. **Testing**: Write tests for your custom job types

## Example Library: Common Job Types

Here's a small library of common job types:

```python
"""
A library of common job types for GigQ.
"""
from gigq import Job

class HTTPRequestJob(Job):
    """Job for making HTTP requests."""

    def __init__(self, name, url, method="GET", headers=None, data=None, **kwargs):
        """
        Initialize an HTTP request job.

        Args:
            name: Name of the job
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            headers: HTTP headers
            data: Request data (for POST, PUT, etc.)
            **kwargs: Additional arguments for the base Job class
        """
        def make_request(url, method, headers, data):
            import requests
            response = requests.request(method, url, headers=headers, data=data)
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                result = response.text

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "result": result
            }

        super().__init__(
            name=name,
            function=make_request,
            params={
                "url": url,
                "method": method,
                "headers": headers,
                "data": data
            },
            **kwargs
        )

class EmailJob(Job):
    """Job for sending emails."""

    def __init__(self, name, to, subject, body, from_email=None, **kwargs):
        """
        Initialize an email job.

        Args:
            name: Name of the job
            to: Recipient email address(es)
            subject: Email subject
            body: Email body
            from_email: Sender email address
            **kwargs: Additional arguments for the base Job class
        """
        def send_email(to, subject, body, from_email):
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['To'] = to
            msg['From'] = from_email or 'noreply@example.com'

            # Get SMTP settings from environment
            import os
            smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
            smtp_port = int(os.environ.get('SMTP_PORT', 25))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.send_message(msg)

            return {"to": to, "subject": subject, "sent": True}

        super().__init__(
            name=name,
            function=send_email,
            params={
                "to": to,
                "subject": subject,
                "body": body,
                "from_email": from_email
            },
            **kwargs
        )

class DatabaseQueryJob(Job):
    """Job for executing database queries."""

    def __init__(self, name, query, params=None, connection_string=None, **kwargs):
        """
        Initialize a database query job.

        Args:
            name: Name of the job
            query: SQL query to execute
            params: Query parameters
            connection_string: Database connection string
            **kwargs: Additional arguments for the base Job class
        """
        def execute_query(query, params, connection_string):
            import os
            import sqlalchemy

            # Use environment variable if connection string not provided
            conn_str = connection_string or os.environ.get('DATABASE_URL')
            if not conn_str:
                raise ValueError("Database connection string not provided")

            engine = sqlalchemy.create_engine(conn_str)
            with engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query), params or {})

                if result.returns_rows:
                    # Get column names
                    columns = result.keys()

                    # Get rows as dictionaries
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]

                    return {
                        "rows": rows,
                        "row_count": len(rows),
                        "columns": columns
                    }
                else:
                    return {
                        "row_count": result.rowcount,
                        "rows": [],
                        "columns": []
                    }

        super().__init__(
            name=name,
            function=execute_query,
            params={
                "query": query,
                "params": params,
                "connection_string": connection_string
            },
            **kwargs
        )
```

## Next Steps

Now that you understand how to create custom job types, you might want to explore:

- [Workflows](../user-guide/workflows.md) - Learn how to create complex workflows with your custom job types
- [Error Handling](../user-guide/error-handling.md) - Learn about error handling strategies
- [Performance Optimization](performance.md) - Optimize performance for your custom job types
