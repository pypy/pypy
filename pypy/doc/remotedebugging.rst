Remote Debugging
=================

PyPy has an experimental remote debugging facility built into the virtual
machine. It can be used to inject arbitrary Python code into another PyPy
process. So far, it works only under Linux. This mechanism is strongly inspired
by `PEP 768`_.

.. _`PEP 768`: https://peps.python.org/pep-0768/

From the commandline
---------------------

To directly execute Python code in another PyPy process, you can run this command::

    pypy -m _pypy_remote_debug <pid> -c <code>

This will cause the other PyPy process with process id ``pid`` the to execute
the ``code`` given.

Alternatively you can pass a script file::

    pypy -m _pypy_remote_debug <pid> <filename>

If the other process is currently blocked by a system call or running a
long-running computation in a C extension, it will not be interrupted. In this
case the script will be executed once that is finished.

For example, to cause the other process to dump its (RPython-level) heap, you
can run::

    pypy -m _pypy_remote_debug -c "import gc; gc.dump_rpy_heap('/tmp/rpy-heap-dump')"

API
---

To execute code remotely from Python code, there is the function
``__pypy__.remote_exec(pid, filename, wait=True)``.

Security
---------

This feature is implemented by writing to the heap memory of another process.
Under Linux, it uses the ``process_vm_writev`` function. This function is
disabled by default on most hardened Linux distributions by Yama_. Therefore
you might need sudo to run the above commands.

.. _Yama: https://www.kernel.org/doc/html/v4.15/admin-guide/LSM/Yama.html#ptrace-scope
