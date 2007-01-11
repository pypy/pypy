#!/usr/bin/env python
""" RPython to javascript compiler
Usage: jscompile module_to_compile [list of functions to export]

- or -
jscompile --help to show list of options
"""

import autopath
import sys, os

from pypy.translator.js.main import rpython2javascript_main, js_optiondescr

from pypy.config.config import Config, to_optparse

def process_options():
    jsconfig = Config(js_optiondescr)
    parser = to_optparse(jsconfig, parserkwargs={"usage": __doc__})
    parser.disable_interspersed_args()
    options, args = parser.parse_args()
    return args, jsconfig

if __name__ == '__main__':
    args, jsconfig = process_options()
    curdir = os.getcwd()
    if curdir not in sys.path:
        sys.path.insert(0, curdir)
    rpython2javascript_main(args, jsconfig)
