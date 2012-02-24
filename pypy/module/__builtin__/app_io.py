# NOT_RPYTHON (but maybe soon)
"""
Plain Python definition of the builtin I/O-related functions.
"""

import sys

def _write_prompt(stdout, prompt):
    print(prompt, file=stdout, end='')
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

def input(prompt=''):
    """input([prompt]) -> string

Read a string from standard input.  The trailing newline is stripped.
If the user hits EOF (Unix: Ctl-D, Windows: Ctl-Z+Return), raise EOFError.
On Unix, GNU readline is used if enabled.  The prompt string, if given,
is printed without a trailing newline before reading."""
    try:
        stdin = sys.stdin
    except AttributeError:
        raise RuntimeError("input: lost sys.stdin")
    try:
        stdout = sys.stdout
    except AttributeError:
        raise RuntimeError("input: lost sys.stdout")

    # hook for the readline module
    if (hasattr(sys, '__raw_input__') and
        isinstance(stdin, file)  and stdin.fileno() == 0 and stdin.isatty() and
        isinstance(stdout, file) and stdout.fileno() == 1):
        _write_prompt(stdout, '')
        return sys.__raw_input__(str(prompt))

    _write_prompt(stdout, prompt)
    line = stdin.readline()
    if not line:    # inputting an empty line gives line == '\n'
        raise EOFError
    if line[-1] == '\n':
        return line[:-1]
    return line

def print_(*args, **kwargs):
    """The new-style print function from py3k."""
    fp = kwargs.pop("file", sys.stdout)
    if fp is None:
        return
    def write(data):
        if not isinstance(data, str):
            data = str(data)
        fp.write(data)
    sep = kwargs.pop("sep", None)
    if sep is not None:
        if not isinstance(sep, str):
            raise TypeError("sep must be None or a string")
    end = kwargs.pop("end", None)
    if end is not None:
        if not isinstance(end, str):
            raise TypeError("end must be None or a string")
    if kwargs:
        raise TypeError("invalid keyword arguments to print()")
    if sep is None:
        sep = " "
    if end is None:
        end = "\n"
    for i, arg in enumerate(args):
        if i:
            write(sep)
        write(arg)
    write(end)
