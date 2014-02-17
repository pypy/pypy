======
 pypy
======

SYNOPSIS
========

``pypy`` [*options*]
[``-c`` *cmd*\ \|\ ``-m`` *mod*\ \|\ *file.py*\ \|\ ``-``\ ]
[*arg*\ ...]

OPTIONS
=======

-i
    Inspect interactively after running script.

-O
    Skip assert statements.

-OO
    Remove docstrings when importing modules in addition to -O.

-c *cmd*
    Program passed in as CMD (terminates option list).

-S
    Do not ``import site`` on initialization.

-s
    Don't add the user site directory to `sys.path`.

-u
    Unbuffered binary ``stdout`` and ``stderr``.

-h, --help
    Show a help message and exit.

-m *mod*
    Library module to be run as a script (terminates option list).

-W *arg*
    Warning control (*arg* is *action*:*message*:*category*:*module*:*lineno*).

-E
    Ignore environment variables (such as ``PYTHONPATH``).

-B
    Disable writing bytecode (``.pyc``) files.

--version
    Print the PyPy version.

--info
    Print translation information about this PyPy executable.

--jit *arg*
    Low level JIT parameters.  Mostly internal.  Run ``--jit help``
    for more information.

ENVIRONMENT
===========

``PYTHONPATH``
    Add directories to pypy's module search path.
    The format is the same as shell's ``PATH``.

``PYTHONSTARTUP``
    A script referenced by this variable will be executed before the
    first prompt is displayed, in interactive mode.

``PYTHONDONTWRITEBYTECODE``
    If set to a non-empty value, equivalent to the ``-B`` option.
    Disable writing ``.pyc`` files.

``PYTHONINSPECT``
    If set to a non-empty value, equivalent to the ``-i`` option.
    Inspect interactively after running the specified script.

``PYTHONIOENCODING``
    If this is set, it overrides the encoding used for
    *stdin*/*stdout*/*stderr*.
    The syntax is *encodingname*:*errorhandler*
    The *errorhandler* part is optional and has the same meaning as in
    `str.encode`.

``PYTHONNOUSERSITE``
    If set to a non-empty value, equivalent to the ``-s`` option.
    Don't add the user site directory to `sys.path`.

``PYTHONWARNINGS``
    If set, equivalent to the ``-W`` option (warning control).
    The value should be a comma-separated list of ``-W`` parameters.

``PYPYLOG``
    If set to a non-empty value, enable logging, the format is:

    *fname*
        logging for profiling: includes all
        ``debug_start``/``debug_stop`` but not any nested
        ``debug_print``.
        *fname* can be ``-`` to log to *stderr*.

    ``:``\ *fname*
        Full logging, including ``debug_print``.

    *prefix*\ ``:``\ *fname*
        Conditional logging.
        Multiple prefixes can be specified, comma-separated.
        Only sections whose name match the prefix will be logged.

    ``PYPYLOG=jit-log-opt,jit-backend:logfile`` will
    generate a log suitable for *jitviewer*, a tool for debugging
    performance issues under PyPy.

.. include:: ../gc_info.rst
   :start-line: 7

SEE ALSO
========

**python**\ (1)
