"""Job functions used in GigQ tests."""
import sqlite3

def simple_job(value):
    """Simple job that doubles the input value."""
    return {"result": value * 2}

def failing_job():
    """Job that deliberately fails."""
    raise ValueError("This job is designed to fail")

def track_execution_job(job_id, tracker_file):
    """
    Job that tracks its execution order.
    
    Args:
        job_id: Identifier for the job
        tracker_file: Path to SQLite database file or a list to append to
    """
    # Check if we're using SQLite tracking (path ends with .db)
    if isinstance(tracker_file, str) and tracker_file.endswith('.db'):
        # SQLite tracking
        conn = sqlite3.connect(tracker_file)
        conn.execute("INSERT INTO execution_order (job_id) VALUES (?)", (job_id,))
        conn.commit()
        conn.close()
    else:
        # Assume it's a list or legacy file path
        try:
            # Try to treat as a list
            if isinstance(tracker_file, list):
                tracker_file.append(job_id)
            else:
                # Legacy file path tracking
                with open(tracker_file, 'a') as f:
                    f.write(f"{job_id}\n")
        except Exception as e:
            print(f"Error in track_execution_job: {e}")
    
    return {"job_id": job_id, "executed": True}

def sleep_job(duration):
    """Job that sleeps for the specified duration."""
    import time
    time.sleep(duration)
    return {"slept_for": duration}

def work_counter_job(job_id, counter_dict):
    """Job that increments a counter in a shared dictionary."""
    import time
    time.sleep(0.1)  # Simulate some work
    if job_id in counter_dict:
        counter_dict[job_id] += 1
    else:
        counter_dict[job_id] = 1
    return {"job_id": job_id, "completed": True, "count": counter_dict[job_id]}

def retry_job(attempts_dict, job_id, fail_times=1):
    """Job that fails a specified number of times before succeeding."""
    if job_id not in attempts_dict:
        attempts_dict[job_id] = 0
    
    attempts_dict[job_id] += 1
    
    if attempts_dict[job_id] <= fail_times:
        raise ValueError(f"Deliberate failure #{attempts_dict[job_id]}")
    
    return {"success": True, "attempts": attempts_dict[job_id]}