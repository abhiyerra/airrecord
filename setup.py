import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="airrecord",
    version="0.0.1",
    author="Abhi Yerra",
    author_email="abhi@opszero.com",
    description="Airtable client to make Airtable interactions a breeze",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abhiyerra/airrecord",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
