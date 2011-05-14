==============================
Cross-translating PyPy for ARM
==============================


Here we describe the setup required and the steps needed to follow to translate
an interpreter using PyPy's translation toolchain to target ARM.

To translate an interpreter for an ARM based platform you can either cross
translate, what we will describe below, or translate directly on the ARM based
system following the normal translation steps, but this is not really feasible
on most ARM powered devices.

To cross translate you run the translation toolchain on a more powerful
machine and generate a binary for ARM using a cross compiler to compile the
generated C code. There are several constraints when doing this. Specially we
currently only support Linux as translation host and target platforms (tested
with Ubuntu). Also you need a 32-bit PyPy or Python to run the translation
toolchain.


Requirements
------------

The tools required to cross translate from Linux to a ARM based Linux are

- A checkout of PyPy's arm-backend-2 branch.
- The GCC arm cross compiler (on Ubuntu it is the gcc-arm-linux-gnueabi package) but other toolchains should also work.
- Scratchbox 2, a cross-compilation engine (scratchbox2 Ubuntu package).
- rootstock (rootstock Ubuntu package).
- A 32-bit PyPy or Python.

Setup
-----

First we will need to create a rootfs image or tarball for the target distribution
(Ubuntu natty in our case) containing the required packages to translate PyPy.

::

  sudo rootstock --fqdn pypysb2 --login pypy --password pypy \
                 --seed build-essential,libgc-dev,libffi-dev \
                 --dist natty

When the rootfs command finishes you should have an archive containing the
created rootfs, create a directory and unpack the archive there. This directory
is going to serve as the scratchbox2 environment.

If you are using the gcc-arm-linux-gnueabi toolchain read the section
Scracthbox 2 issues before continuing.

Go into the directory containing the rootfs and create a Scratchbox 2 environment:

::

  sb2-init -n -c qemu-arm NAME /usr/bin/arm-linux-gnueabi-gcc or codesourcery compiler

Where NAME is the name we choose for the sb2 environment.

Finally, using the newly created scratchbox run the sb2-built-libtool command. 

::

  sb2 -t NAME /usr/bin/sb2-build-libtool  

Now you should have a working cross compilation toolchain in place

Translation
-----------

Having performed all the preliminary steps you should now be able to cross
translate a program for ARM.  You can use this_ minimal
target to test your setup before applying it to a larger project.

First you need to set two environment variables so the translator knows how to
use the scratchbox environment. You need to set the **SB2** environment variable to point to
the path of the unpacked rootfs and the **SB2OPT** should contain the command line
options for the sb2 command. If our rootfs is in the folder /home/user/sb2 and the scratchbox
environment is called "arm", the variables would be defined as follows.


::

  export SB2=~/sb2
  export SB2OPT='-t arm'


Once this is set, you can call the translator 

::

  ~/path_to_pypy_checkout/pypy/translator/goal/translate.py -O1 --platform=arm target.py 

.. _`this`:

::

  def main(args):
      print "Hello World"
      return 0

  def target(*args):
      return main, None


Scracthbox 2 issues
-------------------

At least on Ubuntu, compiling within the scratchbox will fail if you are using the 
arm-linux-gnueabi-gcc compiler. There is a problem with Ubuntu's current version of
scratchbox2, it is fixed in the upcoming release, but that does not help much right now. 
This issue detects some configurations options wrong and adds some flags to the gcc calls that make them
fail. To fix this there is the option to modify Scratchbox 2 itself. In this
case you would need to change the file 

::

  /usr/share/scratchbox2/scripts/sb2-config-gcc-toolchain

Find the line 

::

  echo "" | $GCC_FULLPATH -E - -Wno-poison-system-directories > /dev/null 2>&1

and replace it with 

::

  echo "" | $GCC_FULLPATH -x c - -Wno-poison-system-directories > /dev/null 2>&1

Alternatively after the call to sb2-build-libtool, mentioned above, fails you can edit the files  

::

  ~/.scratchbox2/NAME/sb2.config.d/gcc.config.(sh|lua) 

removing every occurence of -Wno-poison-system-directories and then calling the command again

::

  sb2 -t NAME /usr/bin/sb2-build-libtool  

Following one of the two approaches should yield a working setup.

