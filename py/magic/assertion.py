import __builtin__, sys
from py import magic
from py.__impl__.magic import exprinfo, dyncode

BuiltinAssertionError = __builtin__.AssertionError

class AssertionError(BuiltinAssertionError):
    def __init__(self, *args):
        BuiltinAssertionError.__init__(self, *args)
        f = sys._getframe(1)
        source = dyncode.getparseablestartingblock(f)
        #print "f.f_lineno", f.f_lineno 
        if source:
            self.msg = exprinfo.interpret(source, f)
            if self.msg is None:
                self.msg = "(inconsistenty failed then succeeded)"
            elif self.msg.startswith('AssertionError: '):
                self.msg = self.msg[16:]
            if not self.args:
                self.args = (self.msg,)
        else:
            self.msg = None


def invoke():
    magic.patch(__builtin__, 'AssertionError', AssertionError)
def revoke():
    magic.revert(__builtin__, 'AssertionError') 
