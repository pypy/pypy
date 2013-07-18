======================
What's new in PyPy 2.1
======================

.. this is a revision shortly after release-2.1-beta
.. startrev: 4eb52818e7c0

.. branch: fastjson
Fast json decoder written in RPython, about 3-4x faster than the pure Python
decoder which comes with the stdlib

.. branch: improve-str2charp
Improve the performance of I/O writing up to 15% by using memcpy instead of
copying char-by-char in str2charp and get_nonmovingbuffer

.. branch: flowoperators
Simplify rpython/flowspace/ code by using more metaprogramming.  Create
SpaceOperator class to gather static information about flow graph operations.

.. branch: package-tk
Adapt package.py script to compile CFFI tk extension. Add a --without-tk switch
to optionally skip it.

.. branch: distutils-cppldflags
Copy CPython's implementation of customize_compiler, dont call split on
environment variables, honour CFLAGS, CPPFLAGS, LDSHARED and LDFLAGS on Unices.

.. branch: precise-instantiate
When an RPython class is instantiated via an indirect call (that is, which
class is being instantiated isn't known precisely) allow the optimizer to have
more precise information about which functions can be called. Needed for Topaz.

.. branch: ssl_moving_write_buffer
