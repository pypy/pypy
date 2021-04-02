from __future__ import unicode_literals

import pyrepl.readline
import sys

if sys.version_info < (3,):
    input = raw_input
    value = 


def _test_print():
    # TODO: convert this to an "expect" test
    value = "\x1b[1;31m？>\x1b[0m "
    if sys.version < (3,):
        value = value.encode('utf-8')
    while True:
        try:
            print(input(value))
        except EOFError:
            break
