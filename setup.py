#!/usr/bin/env python
# coding: utf-8

from setuptools import setup
from setuptools import find_packages


def get_packages():
    """ List of (sub)packages to install. """
    return find_packages('.', include=('screenshot', ))


def read_textfile(filename):
    """ Get contents from a text file. """
    with open(filename, 'rU') as fh:
        return fh.read()


def setup_package():
    """ build and run setup. """

    setup(
        name='screenshot',
        description='Find and list modules in the current python environment',
        long_description=read_textfile('README.md'),
        author='fredrikhl',
        url='https://github.com/fredrikhl/screenshot',
        use_scm_version=True,
        setup_requires=['setuptools_scm'],
        packages=get_packages(),
        scripts=['screenshot.py'],
    )


if __name__ == "__main__":
    setup_package()
