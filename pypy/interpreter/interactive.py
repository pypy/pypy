import autopath

from pypy.interpreter import executioncontext, pyframe, baseobjspace
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
        self.space = objspace
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
        from pypy.interpreter import pycode
        r = pycode.PyByteCode()
        r._from_code(code)
        frame = pyframe.PyFrame(self.space, r,
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

    from pypy.tool import option
    from pypy.tool import test
    args = option.process_options(option.get_standard_options(),
                                  None, option.Options)
    objspace = test.objspace(option.Options.spaces[-1])
    con = PyPyConsole(objspace)
    con.interact()
