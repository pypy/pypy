"""
Plain Python definition of the builtin I/O-related functions.
"""

import sys

def execfile(filename, glob=None, loc=None):
    if glob is None:
        caller = sys._getframe(1)
        glob = caller.f_globals
        if loc is None:
            loc = caller.f_locals
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
    try:
        sys.stdin
    except AttributeError:
        raise RuntimeError("[raw_]input: lost sys.stdin");
    try:
        sys.stdout
    except AttributeError:
        raise RuntimeError("[raw_]input: lost sys.stdout");
    if prompt is not None:
        sys.stdout.write(prompt)
        try:
            flush = sys.stdout.flush
        except AttributeError:
            pass
        else:
            flush()
    line = sys.stdin.readline()
    if not line:    # inputting an empty line gives line == '\n'
        raise EOFError
    if line[-1] == '\n':
        return line[:-1]
    return line

def input(prompt=None):
    return eval(raw_input(prompt))
