============================
What's new in PyPy2.7 7.3.3+
============================

.. this is a revision shortly after release-pypy-7.3.3
.. startrev: de512cf13506

.. branch: new-ci-image

CI: Add a Dockerfile for CI to prevent hitting pull limits on docker hub

.. branch: issue-3333

Fix xml.etree.ElementTree assigning default attribute values: issue 3333

.. branch: rpython-rsre-for-37

Support for the new format of regular expressions in Python 3.7

.. branch: rpy-cparser

Upstream internal cparser tool from pypy/ to rpython/


.. branch: win64

Change rpython and pypy to enable translating 64-bit windows


.. branch: rpython-error_value

Introduce @rlib.objectmodel.llhelper_error_value, will be used by HPy

.. branch: add-rffi-constcharpsize2str

Add ``rffi.constcharpsize2str``

.. branch: document-win64

Refactor documentation of win64 from future plans to what was executed

.. branch: sync-distutils

Backport msvc detection from python3, which probably breaks using Visual Studio
2008 (MSVC9, or the version that used to be used to build CPython2.7 on
Windows)

.. branch: py2.7-winreg

Backport fixes to winreg adding reflection and fix for passing None (bpo
21151).
