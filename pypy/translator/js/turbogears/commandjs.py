#!/usr/bin/env python

"""Command-line user interface for rpython2javascript."""

import optparse

from rpython2javascript.pypy.translator.js.main import rpython2javascript_main

class JsCommand:
    "Translate RPython code to Javascript via command-line interface."

    desc = "Translate RPython to Javascript"

    name = None
    package = None
    __version__ = "0.2"
    __author__ = "Eric van Riet Paap"
    __email__ = "eric@vanrietpaap.nl"
    __copyright__ = "Copyright 2006 Eric van Riet Paap"
    __license__ = "MIT"

    def __init__(self, *args, **kwargs):
        parser = optparse.OptionParser(usage="""
%prog [options] <command>

Available commands:
  module <function names>  Translate RPython functions in a module to Javascript
""", version="%prog " + self.__version__)
        self.parser = parser

    def run(self):
        (options, args) = self.parser.parse_args()
        if not args:
            self.parser.error("No command specified")
        #self.options = options
        #command, args = args[0], args[1:]
        #print 'JsCommand:', command, args
        rpython2javascript_main(args)

def main():
    tool = JsCommand()
    tool.run()

if __name__ == '__main__':
    main()
