# NOT_RPYTHON (but maybe soon)
"""
Plain Python definition of the builtin I/O-related functions.
"""

import sys

def execfile(filename, glob=None, loc=None):
    """execfile(filename[, globals[, locals]])

Read and execute a Python script from a file.
The globals and locals are dictionaries, defaulting to the current
globals and locals.  If only globals is given, locals defaults to it."""
    if glob is None:
        # Warning this is at hidden_applevel
        glob = globals()
        if loc is None:
            loc = locals()
    elif loc is None:
        loc = glob
    f = file(filename, 'rU')
    try:
        source = f.read()
    finally:
        f.close()
    #Don't exec the source directly, as this loses the filename info
    co = compile(source.rstrip()+"\n", filename, 'exec')
    exec co in glob, loc

def raw_input(prompt=None):
    """raw_input([prompt]) -> string

Read a string from standard input.  The trailing newline is stripped.
If the user hits EOF (Unix: Ctl-D, Windows: Ctl-Z+Return), raise EOFError.
On Unix, GNU readline is used if enabled.  The prompt string, if given,
is printed without a trailing newline before reading."""
    try:
        stdin = sys.stdin
    except AttributeError:
        raise RuntimeError("[raw_]input: lost sys.stdin")
    try:
        stdout = sys.stdout
    except AttributeError:
        raise RuntimeError("[raw_]input: lost sys.stdout")

    # hook for the readline module
    if (hasattr(sys, '__raw_input__') and
        isinstance(stdin, file)  and stdin.fileno() == 0 and stdin.isatty() and
        isinstance(stdout, file) and stdout.fileno() == 1):
        if prompt is None:
            prompt = ''
        return sys.__raw_input__(prompt)

    if prompt is not None:
        stdout.write(prompt)
        try:
            flush = stdout.flush
        except AttributeError:
            pass
        else:
            flush()
    line = stdin.readline()
    if not line:    # inputting an empty line gives line == '\n'
        raise EOFError
    if line[-1] == '\n':
        return line[:-1]
    return line

def input(prompt=None):
    """Equivalent to eval(raw_input(prompt))."""
    return eval(raw_input(prompt))
