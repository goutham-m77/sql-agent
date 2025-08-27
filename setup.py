from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sql-agent",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A deep agent for intelligent SQL querying and discrepancy detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/sql-agent",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.0.267",
        "openai>=0.27.8",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pydantic>=2.0.0",
    ],
)
