==================================
Getting Started 
==================================

.. contents::

.. _howtopypy: 

What is PyPy ?
==============

PyPy is an implementation of the Python_ programming language written in
Python itself, flexible and easy to experiment with.
We target a large variety of platforms, small and large, by providing a
compiler toolsuite that can produce custom Python versions.  Platform, memory
and threading models, as well as the JIT compiler itself, are aspects of the
translation process - as opposed to encoding low level details into the
language implementation itself. `more...`_


.. _Python: http://docs.python.org/reference/
.. _`more...`: architecture.html

Just the facts 
============== 

Download a pre-built PyPy
-------------------------

The quickest way to start using PyPy is to download a prebuilt binary for your
OS and architecture.  You can either use the `most recent release`_ or one of
our `development nightly build`_.  Please note that the nightly builds are not
guaranteed to be as stable as official releases, use them at your own risk.

.. _`most recent release`: http://pypy.org/download.html
.. _`development nightly build`: http://buildbot.pypy.org/nightly/trunk/

Installing PyPy
---------------

PyPy is ready to be executed as soon as you unpack the tarball or the zip
file, with no need install it in any specific location::

    $ tar xf pypy-1.5-linux.tar.bz2

    $ ./pypy-1.5-linux/bin/pypy
    Python 2.7.1 (?, Apr 27 2011, 12:44:21)
    [PyPy 1.5.0-alpha0 with GCC 4.4.3] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    And now for something completely different: ``implementing LOGO in LOGO:
    "turtles all the way down"''
    >>>>

If you want to make PyPy available system-wide, you can put a symlink to the
``pypy`` executable in ``/usr/local/bin``.  It is important to put a symlink
and not move the binary there, else PyPy would not be able to find its
library.

If you want to install 3rd party libraries, the most convenient way is to
install setuptools_, which will bring ``easy_install`` to you::

    $ wget http://peak.telecommunity.com/dist/ez_setup.py

    $ ./pypy-1.5-linux/bin/pypy ez_setup.py

    $ ls ./pypy-1.5-linux/bin/
    easy_install  easy_install-2.7  pypy

3rd party libraries will be installed in ``pypy-1.5-linux/site-packages``, and
the scripts in ``pypy-1.5-linux/bin``.

Installing using virtualenv
---------------------------

It is often convenient to run pypy inside a virtualenv.  To do this
you need a recent version of virtualenv -- 1.6.1 or greater.  You can
then install PyPy both from a precompiled tarball or from a mercurial
checkout::

	# from a tarball
	$ virtualenv -p /opt/pypy-c-jit-41718-3fb486695f20-linux/bin/pypy my-pypy-env

	# from the mercurial checkout
	$ virtualenv -p /path/to/pypy/pypy/translator/goal/pypy-c my-pypy-env

Note that bin/python is now a symlink to bin/pypy.


Clone the repository
--------------------

If you prefer to `compile PyPy by yourself`_, or if you want to modify it, you
will need to obtain a copy of the sources.  This can be done either by
`downloading them from the download page`_ or by checking them out from the
repository using mercurial.  We suggest using mercurial if one wants to access
the current development.

.. _`downloading them from the download page`: http://pypy.org/download.html

You must issue the following command on your
command line, DOS box, or terminal::

    hg clone http://bitbucket.org/pypy/pypy pypy

This will clone the repository and place it into a directory
named ``pypy``, and will get you the PyPy source in
``pypy/pypy`` and documentation files in ``pypy/pypy/doc``.
We try to ensure that the tip is always stable, but it might
occasionally be broken.  You may want to check out `our nightly tests:`_
find a revision (12-chars alphanumeric string, e.g. "963e808156b3") 
that passed at least the
``{linux32}`` tests (corresponding to a ``+`` sign on the
line ``success``) and then, in your cloned repository, switch to this revision
using::

    hg up -r XXXXX

where XXXXX is the revision id.


.. _`compile PyPy by yourself`: getting-started-python.html
.. _`our nightly tests:`: http://buildbot.pypy.org/summary?branch=<trunk>

Where to go from here
----------------------

After you successfully manage to get PyPy's source you can read more about:

 - `Building and using PyPy's Python interpreter`_
 - `Learning more about the translation toolchain and how to develop (with) PyPy`_

.. _`Building and using PyPy's Python interpreter`: getting-started-python.html
.. _`Learning more about the translation toolchain and how to develop (with) PyPy`: getting-started-dev.html


Understanding PyPy's architecture
---------------------------------

For in-depth information about architecture and coding documentation 
head over to the `documentation section`_ where you'll find lots of 
interesting information.  Additionally, in true hacker spirit, you 
may just `start reading sources`_ . 

.. _`documentation section`: docindex.html 
.. _`start reading sources`: getting-started-dev.html#start-reading-sources

Filing bugs or feature requests 
-------------------------------

You may file `bug reports`_ on our issue tracker which is
also accessible through the 'issues' top menu of 
the PyPy website.  `Using the development tracker`_ has 
more detailed information on specific features of the tracker. 

.. _`Using the development tracker`: coding-guide.html#using-development-tracker
.. _bug reports:            https://codespeak.net/issue/pypy-dev/


.. include:: _ref.txt
