# NOT_RPYTHON    - because print is used
# XXX work on enabling print for flow space
"""
Plain Python definition of the builtin interactive help functions.
"""

import sys

if sys.platform == "win32":
    exit = "Use Ctrl-Z plus Return to exit."
else:
    exit = "Use Ctrl-D (i.e. EOF) to exit."

def copyright():
    print 'Copyright 2003-2004 Pypy development team.\nAll rights reserved.\nFor further information see http://www.codespaek.net/pypy.\nSome materials may have a different copyright.\nIn these cases, this is explicitly noted in the source code file.'

def license():
    print \
"""
Copyright (c) <2003-2004> <Pypy development team>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# Define the built-in 'help'.
# This is a wrapper around pydoc.help (with a twist).

class _Helper:
    def __repr__(self):
        return "Type help() for interactive help, " \
               "or help(object) for help about object."
    def __call__(self, *args, **kwds):
        import pydoc
        return pydoc.help(*args, **kwds)

help = _Helper()
