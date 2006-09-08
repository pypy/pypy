#!/usr/bin/env python
""" RPython to javascript compiler
Usage: jscompiler module_to_compile [list of functions to export]

- or -
jscompiler --help to show list of options
"""

import autopath
import sys

from pypy.translator.js.main import rpython2javascript_main

from pypy.tool import option
import optparse
make_option = optparse.make_option

class Options(option.Options):
    pass

def get_options():
    options = []
    
    options.append(make_option(
        '--view', action='store_true', dest='view',
        help='View flow graphs'))
    
    options.append(make_option(
        '-o', '--output', action='store', type='string', dest='output',
        default='output.js', help='File to save results (default output.js)'))
    
    return options
    
def process_options(argv):
    return option.process_options(get_options(), Options, argv)
    

if __name__ == '__main__':
    argv = process_options(sys.argv[1:])
    rpython2javascript_main(argv, Options)
