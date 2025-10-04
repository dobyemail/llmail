from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llmass",
    version="1.1.15",
    author="Tom Sapletta",
    author_email="",
    description="AI-powered email management: auto-categorize, detect spam, and generate responses with LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dobyemail/llmass",
    project_urls={
        "Bug Tracker": "https://github.com/dobyemail/llmass/issues",
        "Documentation": "https://github.com/dobyemail/llmass#readme",
    },
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    py_modules=[
        "email_organizer",
        "email_responder",
        "email_generator",
        "llmass_cli",
        "test_suite",
    ],
    install_requires=[
        "numpy>=1.21.0",
        "scikit-learn>=1.0.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "accelerate>=0.20.0",
        "sentencepiece>=0.1.99",
        "protobuf>=3.20.0",
        "python-dotenv>=1.0.0",
        "faker>=18.0.0",
        "lorem>=0.1.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "llmass=llmass_cli:main",
            "email-organizer=email_organizer:main",
            "email-responder=email_responder:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Email",
        "Topic :: Communications :: Email :: Filters",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Natural Language :: Polish",
        "Natural Language :: English",
    ],
    keywords="email imap spam categorization llm ai automation",
)