import autopath

from pypy.interpreter import executioncontext, pyframe, baseobjspace
import sys
import code
import linecache


class PyPyConsole(code.InteractiveConsole):
    def __init__(self, objspace):
        code.InteractiveConsole.__init__(self)
        self.space = objspace
        self.ec = executioncontext.ExecutionContext(self.space)
        self.w_globals = self.ec.make_standard_w_globals()
        self.space.setitem(self.w_globals,
                           self.space.wrap("__name__"),
                           self.space.wrap("__main__"))

    def interact(self, banner=None):
        if banner is None:
            banner = "Python %s in pypy\n%s / %s" % (
                sys.version, self.__class__.__name__,
                self.space.__class__.__name__)
        code.InteractiveConsole.interact(self, banner)

    def raw_input(self, prompt=""):
        # add a character to the PyPy prompt so that you know where you
        # are when you debug it with "python -i py.py"
        return code.InteractiveConsole.raw_input(self, prompt[0] + prompt)

    def runcode(self, code):
        # 'code' is a CPython code object
        from pypy.interpreter.pycode import PyCode
        pycode = PyCode()._from_code(code)
        try:
            pycode.exec_code(self.space, self.w_globals, self.w_globals)
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
    from pypy.tool import testit
    args = option.process_options(option.get_standard_options(),
                                  option.Options)
    objspace = option.objspace()
    con = PyPyConsole(objspace)
    con.interact()
