"""
Setup.py script for RPython
"""
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README-rpython.rst'), encoding='utf-8') as f:
    long_description = f.read()

long_description += """
Warning
-------

This is an experimental release of a randomly chosen, untested version of
RPython. Packaging issues are likely, feedback is welcome.
"""

PKG_EXCLUDES = (
    'lib_pypy', 'lib_pypy.*', 'pypy', 'pypy.*',
    'py', 'py.*', '_pytest', '_pytest.*')

setup(
    name='rpython',
    version='0.2.1',
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

    packages=find_packages(exclude=PKG_EXCLUDES),
    package_data={
        'rpython': ['**/*.c', '**/*.h'],
        'rpython.rlib.rvmprof': ['src/shared/**/*.*'],
    },
    # https://github.com/pypa/setuptools/issues/1064
    include_package_data=True,

    install_requires=['pytest<3'],
    entry_points={
        "console_scripts": [
            "rpython = rpython.__main__:main",
        ],
    },
)
