Remote Debugging
=================

PyPy has an experimental remote debugging facility built into the virtual
machine. It can be used to inject arbitrary Python code into another PyPy
process. So far, it works only under Linux.

To start a script in another PyPy process, you can run this command::

    pypy -m _pypy_remote_debug <pid> <scriptfile.py>

This will cause the other PyPy process with process id ``pid`` the to execute
``scriptfile.py``.

If the other process is currently blocked by a system call or running a
long-running computation in a C extension, it will not be interrupted. In this
case the script will be executed once that is finished.

It's also possible to direcly execute some Python code with the ``-c`` option::

    pypy -m _pypy_remote_debug -c "import gc; gc.dump_rpy_heap('/tmp/rpy-heap-dump')"

Security
---------

This feature is implemented by writing to the heap memory of another process.
Under Linux, it uses the ``process_vm_writev`` function. This function is
disabled by default on most hardened Linux distributions by Yama__. Therefore
you might need sudo to run the above commands.

.. __Yama: https://www.kernel.org/doc/html/v4.15/admin-guide/LSM/Yama.html#ptrace-scope
