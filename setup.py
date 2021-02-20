import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cirq_queueing_server",
    version="0.0.1",
    author="Auguste Hirth",
    author_email="ahirth@ucla.edu",
    description="A queueing server for sending jobs to Google's Sycamore device, using Google Cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/achirth/cirq_queueing_server",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.6'
)
