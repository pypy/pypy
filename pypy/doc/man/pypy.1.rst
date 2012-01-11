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
    Dummy optimization flag for compatibility with C Python.

-c *cmd*
    Program passed in as CMD (terminates option list).

-S
    Do not ``import site`` on initialization.

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

--version
    Print the PyPy version.

--info
    Print translation information about this PyPy executable.

--jit *arg*
    Low level JIT parameters. Format is
    *arg*\ ``=``\ *value*\ [``,``\ *arg*\ ``=``\ *value*\ ...]

    ``off``
        Disable the JIT.

    ``threshold=``\ *value*
        Number of times a loop has to run for it to become hot.

    ``function_threshold=``\ *value*
        Number of times a function must run for it to become traced from
        start.

    ``inlining=``\ *value*
        Inline python functions or not (``1``/``0``).

    ``loop_longevity=``\ *value*
        A parameter controlling how long loops will be kept before being
        freed, an estimate.

    ``max_retrace_guards=``\ *value*
        Number of extra guards a retrace can cause.

    ``retrace_limit=``\ *value*
        How many times we can try retracing before giving up.

    ``trace_eagerness=``\ *value*
        Number of times a guard has to fail before we start compiling a
        bridge.

    ``trace_limit=``\ *value*
        Number of recorded operations before we abort tracing with
        ``ABORT_TRACE_TOO_LONG``.

    ``enable_opts=``\ *value*
        Optimizations to enabled or ``all``.
        Warning, this option is dangerous, and should be avoided.

SEE ALSO
========

**python**\ (1)
