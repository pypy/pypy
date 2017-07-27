RPython
=======

RPython is a translation and support framework for producing implementations of
dynamic languages, emphasizing a clean separation between language
specification and implementation aspects.

By separating concerns in this way, it can automatically generate a
Just-in-Time compiler for any dynamic language. It also allows a mix-and-match
approach to implementation decisions, including many that have historically
been outside of a user's control, such as target platform, memory and threading
models, garbage collection strategies, and optimizations applied, including
whether or not to have a JIT in the first place.

Links
-----

* `Documentation <http://rpython.readthedocs.org>`_
* `Bug tracker <https://bitbucket.org/pypy/pypy/issues>`_
* `PyPy project <http://pypy.org>`_
* Mailing list: pypy-dev@python.org
