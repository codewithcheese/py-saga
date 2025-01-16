from setuptools import setup, find_packages

setup(
    name="py-saga",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anyio>=4.0.0",
    ],
)
