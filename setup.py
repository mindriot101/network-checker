# -*- coding: utf-8 -*-


from setuptools import setup
from codecs import open
from os import path

PACKAGE_NAME = "networkcheck"

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as infile:
    long_description = infile.read()

version = {}
with open(path.join(here, PACKAGE_NAME, "version.py")) as infile:
    exec(infile.read(), version)

setup(
    name=PACKAGE_NAME,
    version=version["__version__"],
    description="Check network status",
    url="https://github.com/mindriot101/network-checker",
    long_description=long_description,
    author="Simon Walker",
    author_email="s.r.walker101@googlemail.com",
    license="MIT",
    packages=[PACKAGE_NAME],
    install_requires=["flask"],
    classifiers=[],
    entry_points={
        "console_scripts": ["netcheck-upload = {}.upload:main".format(PACKAGE_NAME)]
    },
)
