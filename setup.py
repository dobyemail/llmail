from setuptools import setup, find_packages

setup(
    name="llmail",
    version="1.0.0",
    author="AI Email Assistant",
    description="AI-powered email organization and response bots",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "scikit-learn>=1.0.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "accelerate>=0.20.0",
        "sentencepiece>=0.1.99",
        "protobuf>=3.20.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "email-organizer=email_organizer:main",
            "email-responder=email_responder:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Email",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)