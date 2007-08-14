#!/usr/bin/env python
""" Interactive (untranslatable) version of the pypy
scheme interpreter
"""
import autopath
from pypy.lang.scheme.object import SchemeException, SchemeQuit,\
        ContinuationReturn
from pypy.lang.scheme.execution import ExecutionContext
from pypy.lang.scheme.ssparser import parse
from pypy.rlib.parsing.makepackrat import BacktrackException
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
        if to_exec == "\n":
            to_exec = ""
        elif check_parens(to_exec):
            try:
                if to_exec == "":
                    print
                    raise SchemeQuit
                print parse(to_exec)[0].eval(ctx).to_string()
            except SchemeQuit, e:
                break
            except ContinuationReturn, e:
                print e.result.to_string()
            except SchemeException, e:
                print "error: %s" % e
            except BacktrackException, e:
                (line, col) = e.error.get_line_column(to_exec)
                expected = " ".join(e.error.expected)
                print "parse error: in line %s, column %s expected: %s" % \
                        (line, col, expected)

            to_exec = ""
            cont = False
        else:
            cont = True

if __name__ == '__main__':
    interactive()
