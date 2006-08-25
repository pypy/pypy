#!/usr/bin/env python
""" RPython to javascript compiler
Usage: jscompiler module_to_compile [list of functions to export]
"""

import autopath
import sys

from pypy.translator.js.main import rpython2javascript_main

if __name__ == '__main__':
    rpython2javascript_main(sys.argv[1:])
