from setuptools import setup, find_packages

setup(
    name="code_assistant",
    version="0.1.0",
    description="Autonomous Code Analysis Assistant",
    packages=find_packages(),
    install_requires=[
        'pyyaml>=6.0',
        'python-dotenv>=1.0.0',
        'psycopg2-binary>=2.9.5'  # Для работы с PostgreSQL
    ],
    entry_points={
        'console_scripts': [
            'codebot=core.cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
)