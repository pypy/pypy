"""
A simple standalone target for the prolog interpreter.
"""

import sys
from prolog.interpreter.translatedmain import repl, execute

# __________  Entry point  __________

from prolog.interpreter.continuation import Engine, jitdriver
from prolog.interpreter import term
from prolog.interpreter import arithmetic # for side effects
from prolog import builtin # for side effects

from rpython.rlib import jit

e = Engine(load_system=True)
term.DEBUG = False

def entry_point(argv):
    e.clocks.startup()
    # XXX crappy argument handling
    for i in range(len(argv)):
        if argv[i] == "--jit":
            if len(argv) == i + 1:
                print "missing argument after --jit"
                return 2
            jitarg = argv[i + 1]
            del argv[i:i+2]
            jit.set_user_param(jitdriver, jitarg)
            break

    if len(argv) == 2:
        execute(e, argv[1])
    if len(argv) > 2:
        print "too many arguments"
        return 2
    try:
        repl(e)
    except SystemExit:
        return 1
    return 0

# _____ Define and setup target ___


def target(driver, args):
    driver.exe_name = 'pyrolog-%(backend)s'
    return entry_point, None

def portal(driver):
    from prolog.interpreter.portal import get_portal
    return get_portal(driver)

def jitpolicy(self):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == '__main__':
    entry_point(sys.argv)
