from pypy.interpreter import executioncontext
from pypy.interpreter import pyframe
from pypy.interpreter import baseobjspace
import sys
import code
import linecache


def offset2lineno(c, stopat):
    tab = c.co_lnotab
    line = c.co_firstlineno
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line = line + ord(tab[i+1])
    return line

class PyPyConsole(code.InteractiveConsole):
    def __init__(self, objspace):
        code.InteractiveConsole.__init__(self)
        self.space = objspace()
        self.ec = executioncontext.ExecutionContext(self.space)
        self.w_globals = self.ec.make_standard_w_globals()
        self.space.setitem(self.w_globals,
                           self.space.wrap("__name__"),
                           self.space.wrap("__main__"))

    def interact(self):
        banner = "Python %s in pypy\n%s / %s" % (
            sys.version, self.__class__.__name__, self.space.__class__.__name__)
        code.InteractiveConsole.interact(self, banner)

    def runcode(self, code):
        frame = pyframe.PyFrame(self.space, code,
                                self.w_globals, self.w_globals)
        try:
            self.ec.eval_frame(frame)
        except baseobjspace.OperationError, operationerr:
            # XXX insert exception info into the application-level sys.last_xxx
            operationerr.print_detailed_traceback(self.space)
        else:
            try:
                if sys.stdout.softspace:
                    print
            except AttributeError:
                # Don't crash if user defined stdout doesn't have softspace
                pass

    def runsource(self, source, ignored_filename="<input>", symbol="single"):
        hacked_filename = '<inline>\n'+source
        try:
            code = self.compile(source, hacked_filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(self.filename)
            return 0
        if code is None:
            return 1
        self.runcode(code)
        return 0

if __name__ == '__main__':
    try:
        import readline
    except ImportError:
        pass
    # object space selection
    if len(sys.argv) < 2:
        choice = 'trivial'   # default
    else:
        choice = sys.argv[1]
    classname = choice.capitalize() + 'ObjSpace'
    module = __import__('pypy.objspace.%s' % choice,
                        globals(), locals(), [classname])
    ObjSpace = getattr(module, classname)
    con = PyPyConsole(ObjSpace)
    con.interact()
