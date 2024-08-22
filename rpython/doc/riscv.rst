.. _riscv:

Cross-Translating for RISC-V
============================

This document describes how to translate RPython to RISC-V 64-bit backend.


Creating a Ubuntu RISC-V 64-bit Chroot
--------------------------------------

This section describes how to set up RISC-V 64-bit chroot on a x86 host.  You
can skip this section if you would like to develop on a RISC-V 64-bit board
directly.

First, we must install dependencies below on the host:

* ``debootstrap`` -- Debian tool to create a Debian/Ubuntu root file system in
  a directory.
* ``schroot`` -- A chroot management daemon that helps us switch between
  chroots.
* ``qemu-user-static`` -- The binary translator that allow us to run RISC-V
  64-bit executables on x86-64.
* ``binfmt-support`` -- A utility package that helps the Linux kernel to invoke
  ``qemu-user-static`` for RISC-V 64-bit executables.
* ``ubuntu-keyring`` -- The public key for Ubuntu archive.

Run the command below to install all of them:

::

    sudo apt-get install debootstrap qemu-user-static binfmt-support schroot

    # For non-Ubuntu host:
    sudo apt-get install ubuntu-keyring

Second, we must decide where we would like to set up the chroot.  In the
example below, ``/srv/chroot/rv64_ubuntu_24_04`` will be used:

Now, we create the root file system by calling:

::

    sudo mkdir -p /srv/chroot

    sudo debootstrap --arch=riscv64 \
        --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg \
        --include=ubuntu-keyring \
        noble \
        /srv/chroot/rv64_ubuntu_24_04 \
        http://ports.ubuntu.com/ubuntu-ports

    # Rename /etc/resolv.conf so that schroot can copy the host resolv.conf
    # into chroot.
    sudo mv /srv/chroot/rv64_ubuntu_24_04/etc/resolv.conf{,.bak}

Third, create a ``default_shm`` schroot profile, which allows the usage of
semaphore and shared memory:

::

    sudo cp /etc/schroot/default /etc/schroot/default_shm

    # Uncomment shm fstab lines
    sudo sed -i 's_#/run_/run_g' /etc/schroot/default_shm/fstab
    sudo sed -i 's_#/dev/shm_/dev/shm_g' /etc/schroot/default_shm/fstab

Fourth, we create a ``schroot`` configuration file for the root file system
we've just created.  The command below creates a configuration file at
``/etc/schroot/chroot.d/rv64_ubuntu_24_04``:

::

    echo "[rv64_ubuntu_24_04]
    description=Ubuntu Noble (24.04) RISC-V
    directory=/srv/chroot/rv64_ubuntu_24_04
    root-users=$(whoami)
    users=$(whoami)
    type=directory
    profile=default_shm" | sudo tee /etc/schroot/chroot.d/rv64_ubuntu_24_04

Now, you can test the chroot with:

::

    schroot -l

You should see the output:

::

    chroot:rv64_ubuntu_24_04

You can enter the chroot with:

::

    schroot -c rv64_ubuntu_24_04

Inside the chroot, if you run ``uname -m``, you should see ``riscv64``:

::

    $ uname -m
    riscv64

You can enter the chroot as the ``root`` user with the ``-u root`` option:

::

    schroot -c rv64_ubuntu_24_04 -u root

You may sometimes need this when you want to install Debian packages to the
chroot.


Build CPython 2.7 for Bootstrapping
-----------------------------------

To run the RPython toolchain, we need a Python 2.7 implementation.  This
section describes how to build a CPython 2.7 from its source code.  You can
skip this section if you already have ``python2.7``.

.. note::

   CPython 2.7 is no longer supported nor maintained.  The instructions below
   is based on my experiment around early 2024.  Please adjust them if needed.


First, install the build dependencies for CPython:

::

    schroot -c rv64_ubuntu_24_04 -u root -- apt-get install \
        build-essential gcc gdb g++ \
        libbz2-dev libdb-dev libexpat1-dev libffi-dev libgdbm-dev \
        libncursesw5-dev libreadline-dev libsqlite3-dev libssl-dev \
        libtinfo-dev tk-dev zlib1g-dev

Secoond, create the final installation directory for CPython:

::

    schroot -c rv64_ubuntu_24_04 -u root -- mkdir /opt/python2

    schroot -c rv64_ubuntu_24_04 -u root -- \
        chown $(whoami):$(whoami) /opt/python2

Third, clone the patched CPython 2.7 repository:

::

    git clone https://github.com/loganchien/cpython27-deprecated -b release_27

    cd cpython27-deprecated

Fourth, build CPython 2.7 in the chroot:

::

    schroot -c rv64_ubuntu_24_04

::

    $ ./configure --prefix=/opt/python2 \
                  --enable-shared \
                  --enable-optimizations \
                  --with-system-ffi LDFLAGS="-Wl,-rpath,/opt/python2/lib"

    $ make -j8

    $ make install -j8

Fifth, set up Python packages:

::

    $ export PATH=/opt/python2/bin:$PATH

    $ python2.7 -mensurepip

    $ python2.7 -mpip install -U pip wheel

Now, you should have a CPython 2.7 that is good enough for RPython translation.


Using the RPython Toolchain
---------------------------

First, install `the dependencies`_ for PyPy development:

.. _`the dependencies`:
   https://doc.pypy.org/en/latest/build.html#install-build-time-dependencies

::

    schroot -c rv64_ubuntu_24_04 -u root -- apt-get install \
        build-essential pkg-config libbz2-dev libexpat1-dev libffi-dev \
        libgc-dev libgdbm-dev liblzma-dev libncurses5-dev libncursesw5-dev \
        libsqlite3-dev libssl-dev tk-dev zlib1g-dev

In addition, to pass all test suites, you will have to build PyPy with git:

::

    schroot -c rv64_ubuntu_24_04 -u root -- apt-get install git


Second, install Python packages for PyPy development:

::

    schroot -c rv64_ubuntu_24_04

    $ export PATH=/opt/python2/bin:$PATH

    $ cd /path/to/pypy/source/tree

    $ python2.7 -mpip install -r requirements.txt


Translate a Hello World Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``target.py`` file with the following content:

::

    def main(args):
        print "Hello World"
        return 0

    def target(*args):
        return main, None

and call the translator:

::

    $ python2.7 rpython/bin/rpython -O2 target.py


If everything worked correctly, this should yield an RISC-V 64-bit binary.
Running this binary on RISC-V 64-bit should produce the output
``Hello World``.


Translate PyPy Interpreter
~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the command below to translate the full PyPy interpreter with a JIT
compiler:

::

    $ cd pypy/goal

    $ python2.7 ../../rpython/bin/rpython --opt=jit targetpypystandalone.py

    $ PYTHONPATH=../.. ./pypy-c ../../lib_pypy/pypy_tools/build_cffi_imports.py

    $ cd ../..

    $ python2.7 pypy/tool/release/package.py --archive-name=pypy-VER-PLATFORM
