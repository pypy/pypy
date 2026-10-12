"""Snippets written in py2-only syntax.

These exist so that the flow space keeps being tested against source the
Python 2 parser accepts and the Python 3 parser does not.  They live apart
from snippet.py so that snippet.py itself can be parsed by both.
"""

from rpython.translator.test.snippet import Exc, exception_deduction0, witness


def exception_deduction_with_raise3(x):
    try:
        exception_deduction0(2)
        if x:
            raise Exc, Exc()
    except Exc as e:
        witness(e)
        return e
    return Exc()
