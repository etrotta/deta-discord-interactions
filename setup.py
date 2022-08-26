from setuptools import setup, find_packages


with open("README.md") as file:
    readme = file.read()


setup(
    name="Deta-Discord-Interactions",
    version="0.0.1",
    url="https://github.com/etrotta/flask-discord-interactions",
    author="etrotta",
    author_email="etrotta@duck.com",
    description="A web framework for Discord interactions specialized for deta.",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms="any",
    install_requires=["requests", "PyNaCl", "requests-toolbelt", "deta"],
    tests_require=["pytest"],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
    ],
    python_requires=">=3.9",
)
