"""
GigQ: A lightweight job queue system with SQLite backend
"""

from .core import Job, JobQueue, Worker, Workflow, JobStatus

# Get version from installed package
try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("gigq")
    except PackageNotFoundError:
        # Package is not installed
        __version__ = "0.1.0"  # Default development version
except ImportError:
    # Fallback for Python < 3.8
    try:
        from importlib_metadata import version, PackageNotFoundError
        try:
            __version__ = version("gigq")
        except PackageNotFoundError:
            __version__ = "0.1.0"  # Default development version
    except ImportError:
        __version__ = "0.1.0"  # Default development version

__all__ = ["Job", "JobQueue", "Worker", "Workflow", "JobStatus"]