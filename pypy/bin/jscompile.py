#!/usr/bin/env python
""" RPython to javascript compiler
Usage: jscompiler module_to_compile [list of functions to export]

- or -
jscompiler --help to show list of options
"""

import autopath
import sys, os

from pypy.translator.js.main import rpython2javascript_main, Options

from pypy.tool import option
from py.compat import optparse
make_option = optparse.make_option

def get_options():
    options = []
    
    options.append(make_option(
        '--view', action='store_true', dest='view',
        help='View flow graphs'))
    
    options.append(make_option(
        '-o', '--output', action='store', type='string', dest='output',
        help='File to save results (default output.js)'))
    
    options.append(make_option(
        '-d', '--debug', action='store_true', dest='debug_transform',
        help="Use !EXPERIMENTAL! debug transform to produce tracebacks"
    ))
    
    return options
    
def process_options(argv):
    return option.process_options(get_options(), Options, argv)

if __name__ == '__main__':
    argv = process_options(sys.argv[1:])
    curdir = os.getcwd()
    if curdir not in sys.path:
        sys.path.insert(0, curdir)
    rpython2javascript_main(argv, Options)
