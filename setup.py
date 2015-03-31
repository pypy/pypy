"""
Setup.py script for RPython
"""
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README-rpython.rst'), encoding='utf-8') as f:
    long_description = f.read()

long_description += """
Warning
-------

This is an experimental release of a randomly chosen, untested version of
RPython. Packaging issues are likely, feedback is welcome.
"""

setup(
    name='rpython',
    version='0.1.2',
    description='RPython',
    long_description=long_description,

    url='https://rpython.readthedocs.org',
    author='The PyPy team',
    author_email='pypy-dev@python.org',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='development',

    packages=find_packages(),  # MANIFEST.in filters out all the pypy stuff
    package_data={'rpython': ['translator/c/src/*.c', 'translator/c/src/*.h']},
    install_requires=['pytest'],
)
