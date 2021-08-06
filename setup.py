import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysolarfrontier",
    version="1.0",
    author="coen800",
    description="Library to communicate with Solar Frotier inverters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/coen800/pysolarfrontier",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
