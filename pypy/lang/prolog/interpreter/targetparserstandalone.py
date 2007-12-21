from pypy.lang.prolog.interpreter.eclipseprologparser import parse

def entry_point(args):
    if len(args) > 1:
        t = parse(args[1])
        return 0
    return -1

def target(driver, args):
    return entry_point, None
