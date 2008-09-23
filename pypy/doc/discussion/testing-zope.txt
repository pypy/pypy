Testing Zope on top of pypy-c
=============================

Getting Zope packages
---------------------

If you don't have a full Zope installation, you can pick a Zope package,
check it out via Subversion, and get all its dependencies (replace
``$PKG`` with, for example, ``zope.interface``)::

    svn co svn://svn.zope.org/repos/main/$PKG/trunk $PKG
    cd $PKG
    python bootstrap.py
    bin/buildout
    bin/test

Required pypy-c version
-----------------------

You probably need a pypy-c built with --allworkingmodules, at least::

    cd pypy/translator/goal
    ./translate.py targetpypystandalone.py --allworkingmodules

Workarounds
-----------

At the moment, our ``gc`` module is incomplete, making the Zope test
runner unhappy.  Quick workaround: go to the
``lib-python/modified-2.4.1`` directory and create a
``sitecustomize.py`` with the following content::

    print "<adding dummy stuff into the gc module>"
    import gc
    gc.get_threshold = lambda : (0, 0, 0)
    gc.get_debug = lambda : 0
    gc.garbage = []

Running the tests
-----------------

To run the tests we need the --oldstyle option, as follows::

    cd $PKG
    pypy-c --oldstyle bin/test
