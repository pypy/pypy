#!/usr/bin/env python
""" Interactive (untranslatable) version of the pypy
scheme interpreter
"""
import autopath
from pypy.lang.scheme.object import ExecutionContext, SchemeException, \
        SchemeQuit
from pypy.lang.scheme.ssparser import parse, SchemeParsingError
import os, sys

def check_parens(s):
    return s.count("(") == s.count(")")

def interactive():
    print "PyPy Scheme interpreter"
    ctx = ExecutionContext()
    to_exec = ""
    cont = False
    while 1:
        if cont:
            ps = '.. '
        else:
            ps = '-> '
        sys.stdout.write(ps)
        to_exec += sys.stdin.readline()
        if check_parens(to_exec):
            try:
                print parse(to_exec).eval(ctx)
            except SchemeQuit, e:
                break
            except SchemeException, e:
                print "error: %s" % e
            except SchemeParsingError, e:
                print "syntax error"

            to_exec = ""
            cont = False
        else:
            cont = True

if __name__ == '__main__':
    interactive()
