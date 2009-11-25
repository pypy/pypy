What you need to run CLI jit tests
==================================

Translated tests
-----------------

Recent versions of mono contains a bug that prevents jit tests to run correctly:
http://bugzilla.novell.com/show_bug.cgi?id=474718

To run them, you either need:

  - an old version of mono (1.9 is known to work; probably versions up to 2.2
    works too but I'm not sure)

  - to run mono with -O=-branch; something like alias mono="mono -O=-branch"
    should work, but I never tried


Direct tests
------------

You need Pythonnet: instructions on how to install it are here:
http://codespeak.net/pypy/dist/pypy/doc/cli-backend.html
