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

Clone the repository
--------------------

Before you can play with PyPy, you will need to obtain a copy
of the sources.  This can be done either by `downloading them
from the download page`_ or by checking them out from the
repository using mercurial.  We suggest using mercurial if one
wants to access the current development.

.. _`downloading them from the download page`: http://pypy.org/download.html

If you choose to use mercurial,
first make sure you have ``subversion`` installed.
You must issue the following command on your
command line, DOS box, or terminal::

    hg clone http://bitbucket.org/pypy/pypy pypy

If you get an error like this::

    abort: repository [svn]http://codespeak.net/svn/pypy/build/testrunner not found!

it probably means that your mercurial version is too old. You need at least
Mercurial 1.6 to clone the PyPy repository.

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

.. _`our nightly tests:`: http://buildbot.pypy.org/summary?branch=<trunk>

If you want to commit to our repository on bitbucket, you will have to
install subversion in addition to mercurial.

Installing using virtualenv
---------------------------

It is often convenient to run pypy inside a virtualenv.  To do this
you need a recent version of virtualenv -- 1.5 or greater.  You can
then install PyPy both from a precompiled tarball or from a mercurial
checkout::

	# from a tarball
	$ virtualenv -p /opt/pypy-c-jit-41718-3fb486695f20-linux/bin/pypy my-pypy-env

	# from the mercurial checkout
	$ virtualenv -p /path/to/pypy/pypy/translator/goal/pypy-c my-pypy-env

Note that bin/python is now a symlink to bin/pypy.


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


.. include:: _ref.rst
