"""

capture stdout/stderr 

"""
import sys
try: from cStringIO import StringIO
except ImportError: from StringIO import StringIO

class SimpleOutErrCapture:
    """ capture sys.stdout/sys.stderr (but not system level fd 1 and 2). 
   
    this captures only "In-Memory" and is currently intended to be
    used by the unittest package to capture print-statements in tests. 
    """
    def __init__(self):
        self.oldout = sys.stdout
        self.olderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()


    def reset(self):
        """ return captured output and restore sys.stdout/err."""
        o,e = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = self.oldout, self.olderr
        del self.oldout, self.olderr
        out = o.getvalue()
        err = e.getvalue()
        return out, err
