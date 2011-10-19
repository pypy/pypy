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

def raw_input(prompt=''):
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

    print >> stdout, prompt,
    try:
        flush = stdout.flush
    except AttributeError:
        pass
    else:
        flush()
    try:
        stdout.softspace = 0
    except (AttributeError, TypeError):
        pass
    line = stdin.readline()
    if not line:    # inputting an empty line gives line == '\n'
        raise EOFError
    if line[-1] == '\n':
        return line[:-1]
    return line

def input(prompt=None):
    """Equivalent to eval(raw_input(prompt))."""
    return eval(raw_input(prompt))

def print_(*args, **kwargs):
    """The new-style print function from py3k."""
    fp = kwargs.pop("file", sys.stdout)
    if fp is None:
        return
    def write(data):
        if not isinstance(data, basestring):
            data = str(data)
        fp.write(data)
    want_unicode = False
    sep = kwargs.pop("sep", None)
    if sep is not None:
        if isinstance(sep, unicode):
            want_unicode = True
        elif not isinstance(sep, str):
            raise TypeError("sep must be None or a string")
    end = kwargs.pop("end", None)
    if end is not None:
        if isinstance(end, unicode):
            want_unicode = True
        elif not isinstance(end, str):
            raise TypeError("end must be None or a string")
    if kwargs:
        raise TypeError("invalid keyword arguments to print()")
    if not want_unicode:
        for arg in args:
            if isinstance(arg, unicode):
                want_unicode = True
                break
    if want_unicode:
        newline = u"\n"
        space = u" "
    else:
        newline = "\n"
        space = " "
    if sep is None:
        sep = space
    if end is None:
        end = newline
    for i, arg in enumerate(args):
        if i:
            write(sep)
        write(arg)
    write(end)
