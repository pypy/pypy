Welcome to RPython's documentation!
===================================

RPython is a translation and support framework for producing implementations of
dynamic languages, emphasizing a clean separation between language
specification and implementation aspects.

By separating concerns in this way, our implementation of Python - and other
dynamic languages - is able to automatically generate a Just-in-Time compiler
for any dynamic language.  It also allows a mix-and-match approach to
implementation decisions, including many that have historically been outside of
a user's control, such as target platform, memory and threading models, garbage
collection strategies, and optimizations applied, including whether or not to
have a JIT in the first place.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 1

   getting-started
   faq
   rpython
   rlib
   rffi
   translation
   rtyper
   garbage_collection
   windows


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
