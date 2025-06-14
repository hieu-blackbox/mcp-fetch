#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mcp-fetch",
    version="0.8.11",
    author="kazuph",
    description="A Model Context Protocol server that provides web content fetching capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kazuph/mcp-fetch",
    py_modules=["main"],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcp-fetch=main:main",
        ],
    },
    keywords=["mcp", "fetch", "web", "content", "model-context-protocol"],
)
