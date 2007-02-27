#!/usr/bin/env python
# encoding: utf-8
"""
js_interactive.py
"""

import autopath
import sys
import getopt
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Builtin, W_String, ThrowException, w_Undefined
from pypy.lang.js import jsparser
import os
import cmd

help_message = """
PyPy's JavaScript Interpreter:
 -f filename - Loads a file
 -n to not be interactive
 -h show this help message
 -d jump to a pdb in case of failure
"""

interactive = True

def setup_readline():
    import readline
    import os
    histfile = os.path.join(os.environ["HOME"], ".jspypyhist")
    try:
        getattr(readline, "clear_history", lambda : None)()
        readline.read_history_file(histfile)
    except IOError:
        pass
    import atexit
    atexit.register(readline.write_history_file, histfile)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def loadjs(ctx, args, this):
    filename = args[0]
    f = open(filename.ToString())
    t = load_source(f.read())
    f.close()
    return t.execute(ctx)

def tracejs(ctx, args, this):
    arguments = args
    import pdb
    pdb.set_trace()

def quitjs(ctx, args, this):
    sys.exit(0)
    
    
def main(argv=None):
    # XXX: note. This will not work when translated, because
    # globals cannot be modified (ie. interactive is always True).
    # so I'm adding support which will not be translated, probably
    # for further consideration
    global interactive
    debug = False
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hdnf:", ["help",])
        except getopt.error, msg:
            raise Usage(msg)
    
        # option processing
        filenames = []
        for option, value in opts:
            if option == "-f":
                filenames.append(value)
            if option == "-n":
                interactive = False
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option == '-d':
                debug = True
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2
    
    interp = Interpreter()
        
    interp.w_Global.Put('quit', W_Builtin(quitjs))
    interp.w_Global.Put('load', W_Builtin(loadjs))
    interp.w_Global.Put('trace', W_Builtin(tracejs))
    for filename in filenames:
        try:
            loadjs(interp.global_context, [W_String(filename)], None)
            # XXX we should catch more stuff here, like not implemented
            # and such
        except (jsparser.JsSyntaxError, ThrowException), e:
            if isinstance(e, jsparser.JsSyntaxError):
                print "\nSyntax error!"
            elif isinstance(e, ThrowException):
                print "\nJS Exception thrown!"
            return

    #while interactive:
    #    res = interp.run(load_source(raw_input("js-pypy> ")))
    #    if res is not None:
    #        print res
    if interactive:
        MyCmd(interp, debug).cmdloop()

class MyCmd(cmd.Cmd):
    prompt = "js-pypy> "
    def __init__(self, interp, debug):
        cmd.Cmd.__init__(self)
        setup_readline()
        self.debug = debug
        self.interp = interp
        self.reset()

    def reset(self):
        self.prompt = self.__class__.prompt
        self.lines = []
        self.level = 0
    
    def default(self, line):
        # let's count lines and continue till matching proper nr of {
        # XXX: '{' will count as well
        # we can avoid this by using our own's tokeniser, when we possess one
        if line == 'EOF':
            print "\nQuitting"
            sys.exit()
        opens = line.count('{')
        closes = line.count('}')
        self.level += opens - closes
        self.lines.append(line)
        if self.level > 0:
            self.prompt = '     ... '
            return
        elif self.level < 0:
            print "\nError!!! Too many closing braces"
            self.level = 0
            return
        try:
            try:
                res = self.interp.run(load_source("\n".join(self.lines)))
                # XXX we should catch more stuff here, like not implemented
                # and such
            except (jsparser.JsSyntaxError, ThrowException), e:
                e_info = sys.exc_info()
                if self.debug:
                    import pdb
                    pdb.post_mortem(e_info[2])
                else:
                    if isinstance(e, jsparser.JsSyntaxError):
                        print "\nSyntax error!"
                    elif isinstance(e, ThrowException):
                        print e.exception.ToString()
                return
        finally:
            self.reset()
        if (res is not None) and (res is not w_Undefined):
            try:
                print res.GetValue().ToString()
            except ThrowException, e:
                print e.exception.ToString()

if __name__ == "__main__":
    import py
    py.test.config.parse([])
    sys.exit(main())
