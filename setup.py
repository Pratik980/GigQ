"""
GigQ setup configuration
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gigq",
    version="0.1.0",
    author="GigQ Team",
    author_email="info@gigq.dev",
    description="A lightweight job queue system with SQLite backend",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gigq/gigq",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
    install_requires=[
        "importlib-metadata>=1.0; python_version < '3.8'",
    ],
    entry_points={
        "console_scripts": [
            "gigq=gigq.cli:main",
        ],
    },
)
