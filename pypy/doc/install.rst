Downloading and Installing PyPy
===============================

Using a packaged PyPy
~~~~~~~~~~~~~~~~~~~~~

Some Linux distributions provide a pypy package. Note that in order to
install additional modules that require compilation, you may need to install
additional packages such as pypy-dev. This will manifest as an error about
"missing Python.h". Distributions do not as of yet supply many pypy-ready
packages, if you require additionall modules we recommend creating a virtualenv
and using pip. 

.. _prebuilt-pypy:
Download a pre-built PyPy
~~~~~~~~~~~~~~~~~~~~~~~~~

The quickest way to start using PyPy is to download a prebuilt binary for your
OS and architecture.  You can either use the `most recent release`_ or one of
our `development nightly build`_.  Please note that the nightly builds are not
guaranteed to be as stable as official releases, use them at your own risk.

.. _most recent release: http://pypy.org/download.html
.. _development nightly build: http://buildbot.pypy.org/nightly/trunk/


Installing PyPy
~~~~~~~~~~~~~~~

PyPy is ready to be executed as soon as you unpack the tarball or the zip
file, with no need to install it in any specific location:

.. code-block:: console

    $ tar xf pypy-2.1.tar.bz2
    $ ./pypy-2.1/bin/pypy
    Python 2.7.3 (480845e6b1dd, Jul 31 2013, 11:05:31)
    [PyPy 2.1.0 with GCC 4.4.3] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    And now for something completely different: ``PyPy is an exciting technology
    that lets you to write fast, portable, multi-platform interpreters with less
    effort''
    >>>>

If you want to make PyPy available system-wide, you can put a symlink to the
``pypy`` executable in ``/usr/local/bin``.  It is important to put a symlink
and not move the binary there, else PyPy would not be able to find its
library.

Installing more modules
~~~~~~~~~~~~~~~~~~~~~~~

If you want to install 3rd party libraries, the most convenient way is
to install pip_ using ensurepip_ (unless you want to install virtualenv as 
explained below; then you can directly use pip inside virtualenvs):

.. code-block:: console

    $ ./pypy-xxx/bin/pypy -m ensurepip
    $ ./pypy-xxx/bin/pip install pygments  # for example

Third party libraries will be installed in ``pypy-xxx/site-packages``, and
the scripts in ``pypy-xxx/bin``.


Installing using virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is often convenient to run pypy inside a virtualenv.  To do this
you need a recent version of virtualenv -- 1.6.1 or greater.  You can
then install PyPy both from a precompiled tarball or from a mercurial
checkout::

	# from a tarball
	$ virtualenv -p /opt/pypy-xxx/bin/pypy my-pypy-env

	# from the mercurial checkout
	$ virtualenv -p /path/to/pypy/pypy/translator/goal/pypy-c my-pypy-env

Note that bin/python is now a symlink to bin/pypy.

.. _pip: http://pypi.python.org/pypi/pip
.. _ensurepip: https://docs.python.org/2.7/library/ensurepip.html

Building PyPy yourself
~~~~~~~~~~~~~~~~~~~~~~

If you're interested in getting more involved, or doing something different with
PyPy, consult :doc:`the build instructions <build>`.
