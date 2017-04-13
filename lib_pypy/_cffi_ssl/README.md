# PyPy's SSL module

All of the CFFI code is copied from cryptography, wich patches contributed
back to cryptography. PyPy vendors it's own copy of the cffi backend thus
it renames the compiled shared object to _pypy_openssl.so (which means
that cryptography can ship their own cffi backend)

NOTE: currently, we have changed ``_cffi_src/openssl/callbacks.py`` to
not rely on the CPython C API.

# Tests?

Currently this module is tested using CPython's standard library test suite.

# Install it into PyPy's source tree

Copy over all the sources into the folder `lib_pypy/_cffi_ssl/*`. Updating the cffi backend can be simply done by the following command::

    $ cp -r <cloned cryptography folder>/src/_cffi_src/* .

NOTE: you need to keep our version of ``_cffi_src/openssl/callbacks.py``
for now!

# Crpytography version

Copied over release version `1.7.2`
