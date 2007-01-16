#!/usr/bin/env python
# encoding: utf-8
"""
js_interactive.py
"""

import autopath
import sys
import getopt
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Builtin, W_String

help_message = '''
Pypy Javascript Interpreter:
 -f filname Load a file
 -h show this help message
'''


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def loadjs(ctx, args, this):
    filename = args[0]
    f = open(filename.ToString())
    t = load_source(f.read())
    f.close()
    return t.execute(ctx)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hf:", ["help",])
        except getopt.error, msg:
            raise Usage(msg)
    
        # option processing
        filenames = []
        for option, value in opts:
            if option == "-f":
                filenames.append(value)
            if option in ("-h", "--help"):
                raise Usage(help_message)
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2
    
    interp = Interpreter()
    def quiter(ctx, args, this):
        sys.exit(0)
        return "this should not be printed"
    
    interp.w_Global.Put('quit', W_Builtin(quiter))
    interp.w_Global.Put('load', W_Builtin(loadjs))
    for filename in filenames:
        loadjs(interp.global_context, [W_String(filename)], None)

    while 1:
        res = interp.run(load_source(raw_input("pypy-js> ")))
        if res is not None:
            print res


if __name__ == "__main__":
    sys.exit(main())
