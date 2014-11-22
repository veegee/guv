#!/usr/bin/env python
from setuptools import find_packages, setup
from guv import __version__
from os import path


classifiers=[
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.2",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Topic :: Internet",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Intended Audience :: Developers",
    "Development Status :: 2 - Pre-Alpha",
]

setup(
    name='guv',
    version=__version__,
    description='Python 3 networking library based on greenlets and libuv',
    author='V G',
    author_email='veegee@veegee.org',
    url='http://guv.readthedocs.org',
    packages=find_packages(exclude=['tests', 'benchmarks']),
    install_requires=['greenlet>=0.4.0', 'cffi>=0.8.0'],
    zip_safe=False,
    long_description=open(path.join(path.dirname(__file__), 'README.rst')).read(),
    tests_require=['pytest>=2.6'],
    classifiers=classifiers
)
