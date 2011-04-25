How to run PyPy on top of maemo platform
========================================

This howto explains how to use Scratchbox_ to cross-compile PyPy's 
Python Interpreter to an `Internet-Tablet-OS`_, more specifically 
the Maemo_ platform.  This howto should work well for getting
a usable Python Interpreter for Nokia's N810_ device. 

setup cross-compilation environment
-------------------------------------

The main steps are to install scratchbox and the Maemo SDK.  Please refer 
to Nokia's `INSTALL.txt`_ for more detail. 

Adjust linux kernel settings
+++++++++++++++++++++++++++++++++

In order to install and run scratchbox you will need to adjust
your Linux kernel settings.  Note that the VDSO setting may
crash your computer - if that is the case, try running without
this setting. You can try it like this::

   $ echo 4096 | sudo tee /proc/sys/vm/mmap_min_addr
   $ echo 0 | sudo tee /proc/sys/vm/vdso_enabled 

If that works fine for you (on some machines the vdso setting can freeze machines) 
you can make the changes permanent by editing ``/etc/sysctl.conf`` to contain::

    vm.vdso_enabled = 0
    vm.mmap_min_addr = 4096

install scratchbox packages
+++++++++++++++++++++++++++++++++

Download 

	http://repository.maemo.org/stable/diablo/maemo-scratchbox-install_4.1.1.sh

and run this script as root::

  $ sh maemo-scratchbox-install_4.1.1.sh -s /scratchbox -u ACCOUNTNAME 

The script will automatically download Debian packages or tarballs 
and pre-configure a scratchbox environment with so called "devkits" 
and "toolchains" for performing cross-compilation.  It's fine
and recommended to use your linux account name as a scratchbox 
ACCOUNTNAME. 

It also sets up an "sbox" group on your system and makes you
a member - giving the right to login to a scratchbox environment. 

testing that scratchbox environment works
+++++++++++++++++++++++++++++++++++++++++++++++

Login freshly to your Linux account in order to activate 
your membership in the "sbox" unix group and then type::

  $ /scratchbox/login 

This should warn you with something like "sb-conf: no current
target" because we have not yet created a cross-compilation
target.  

Note that Scratchbox starts daemon services which 
can be controlled via::

    /scratchbox/sbin/sbox_ctl start|stop


Installing the Maemo SDK 
+++++++++++++++++++++++++++++++

To mimic the specific N810_ environment we now install the Maemo-SDK.  
This will create an target within our new scratchbox environment 
that we then use to compile PyPy.  

Make sure that you are a member of the "sbox" group - this might
require logging out and in again. 

Then, download 

   http://repository.maemo.org/stable/diablo/maemo-sdk-install_4.1.1.sh

and execute it with user privileges::

   $ sh maemo-sdk-install_4.1.1.sh

When being asked select the default "Runtime + Dev" packages.  You do not need 
Closed source Nokia binaries for PyPy.  This installation
script will download "rootstraps" and create so called
"targets" and preselect the "DIABLO_ARMEL" target for ARM
compilation.  Within the targets a large number of packages
will be pre-installed resulting in a base scratchbox
environment that is usable for cross compilation of PyPy.  

Customizing the DIABLO_ARMEL target for PyPy
++++++++++++++++++++++++++++++++++++++++++++++++

As PyPy does not yet provide a debian package description
file for use on Maemo, we have to install some dependencies manually
into our Scratchbox target environment.  

1. Go into your scratchbox by executing ``/scratchbox/login``
   (this should bring you to a shell with the DIABLO_ARMEL target) 

2. Add these lines to ``/etc/apt/sources.list``::

    deb http://repository.maemo.org/extras/ diablo free non-free
    deb http://repository.maemo.org/extras-devel/ diablo free non-free

   NOTE: if you have an older version of Maemo on your device you 
   can try substitute "chinook" for "diablo" in the above lines 
   and/or update your firmware.  You can probably see which version
   you are using by looking at the other content of the ``sources.list``. 

3. Perform ``apt-get update``.

4. Install some necessary packages::

     apt-get install python2.5-dev libffi4-dev zlib1g-dev libbz2-dev libgc-dev libncurses5-dev 

   The "libgc-dev" package is only needed if you want to use the Boehm
   garbage collector. 

5. Leave the scratchbox shell again with ``exit``. 


Translating PyPy for the Maemo platform
------------------------------------------

You at least need "gcc" and "libc-dev" packages on your host system 
to compile pypy.  The scratchbox and its DIABLO_ARMEL target contains 
its own copies of GCC, various C libraries and header files
which pypy needs for successful cross-compilation.  

Now, on the host system, perform a mercurial clone of PyPy::

    hg clone ssh://hg@bitbucket.org/pypy/pypy

Several revisions since about 9d7b7ecb9144 are known to work and
the last manually tested one is currently 7f267e4b7861.  

Change to the ``pypy-trunk/pypy/translator/goal`` directory and execute::

    python translate.py --platform=maemo --opt=3

You need to run translate.py using Python 2.5.  This will last some 30-60
minutes on most machines.  For compiling the C source code PyPy's tool chain
will use our scratchbox/Maemo cross-compilation environment. 

When this step succeeds, your ``goal`` directory will contain a binary called
``pypy-c`` which is executable on the Maemo device. To run this binary
on your device you need to also copy some support files. A good way to 
perform copies to your device is to install OpenSSH on the
mobile device and use "scp" or rsync for transferring files.

You can just copy your whole pypy-trunk directory over to your mobile 
device - however, only these should be needed::

    lib/pypy1.2/lib_pypy
    lib/pypy1.2/lib-python
    pypy/translator/goal/pypy-c

It is necessary that the ``pypy-c`` can find a "lib-python" and "lib_pypy" directory
if you want to successfully startup the interpreter on the device. 

Start ``pypy-c`` on the device. If you see an error like "setupterm: could not find terminal" 
you probably need to perform this install on the device::

    apt-get install ncurses-base

Eventually you should see something like::

    Nokia-N810-51-3:~/pypy/trunk# ./pypy-c
    Python Python 2.5.2 (pypy 1.0.0 build 59527) on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    And now for something completely different: ``E09 2K @CAA:85?''
    >>>> 

    
.. _N810: http://en.wikipedia.org/wiki/Nokia_N810
.. _`Internet-Tablet-OS`: http://en.wikipedia.org/wiki/Internet_Tablet_OS
.. _Maemo: http://www.maemo.org 
.. _Scratchbox: http://www.scratchbox.org 
.. _`INSTALL.txt`: http://tablets-dev.nokia.com/4.1/INSTALL.txt


