# Standard imports
import sys
import code
import keyword

assert sys.version_info >= (2,3), "sorry, can only run with python2.3 and greater"

try:
    import readline
    have_readline = True
    
except:
    have_readline = False
    

# PyPy imports
import autopath

from pypy.tool import pydis
from pypy.tool.traceop import print_result

from pypy.interpreter import executioncontext, pyframe, baseobjspace
from pypy.interpreter.baseobjspace import ObjSpace

from pypy.objspace import trace


#//////////////////////////////////////////////////////////////////////////

if have_readline:

    class Completer:
        def __init__(self, space):
            self.space = space

        def complete(self, text, state):

            if state == 0:
                if "." in text:
                    self.matches = self.attr_matches(text)
                else:
                    self.matches = self.global_matches(text)
            try:
                return self.matches[state]

            except IndexError:
                return None


        def global_matches(self, text):
            
            import __builtin__            

            w_res = self.space.call_method(self.space.w_globals, "keys")
            namespace_keys = self.space.unwrap(w_res)

            matches = []
            n = len(text)
            
            for l in [namespace_keys, __builtin__.__dict__.keys(), keyword.kwlist]:
                for word in l:
                    if word[:n] == text and word != "__builtins__":
                        matches.append(word)
            
            return matches

        def attr_matches(self, text):
            import re
            m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
            if not m:
                return

            expr, attr = m.group(1, 3)
            s = self.space
            w_obj = s.getitem(s.w_globals, s.wrap(expr))
            w_func = s.getitem(s.w_builtins, s.wrap("dir"))
            w_res = s.call_function(w_func, w_obj)
            words = s.unwrap(w_res)
            matches = []
            n = len(attr)
            for word in words:

                if word[:n] == attr and word != "__builtins__":
                    matches.append("%s.%s" % (expr, word))

            return matches


#//////////////////////////////////////////////////////////////////////////

class TraceConsole(code.InteractiveConsole):
    def __init__(self, space):
        code.InteractiveConsole.__init__(self)
        s = self.space = trace.TraceObjSpace(space)
        s.setitem(s.w_globals, s.wrap("__pytrace__"), s.w_True)
        self.objspacename = space.__class__.__name__


    def interact(self, banner=None):
        if banner is None:
            banner = "Python %s in pypy(trace)\n%s / %s - %s" % (
                sys.version, self.__class__.__name__,
                self.space,
                " [Use  __pytrace__ flag to turn off tracing.]" )
        code.InteractiveConsole.interact(self, banner)


    def raw_input(self, prompt=""):
        # add a character to the PyPy prompt so that you know where you
        # are when you debug it with "python -i py.py"
        return code.InteractiveConsole.raw_input(self, prompt[0] + prompt)


    def runcode(self, code):
        # 'code' is a CPython code object
        from pypy.interpreter.pycode import PyCode
        pycode = PyCode()._from_code(code)

        s = self.space
        trace_flag = s.unwrap(s.getitem(s.w_globals,
                                        s.wrap("__pytrace__")))
        if trace_flag:
            s.settrace()

        try:
            pycode.exec_code(s, s.w_globals, s.w_globals)
            if trace_flag:
                res = s.getresult()
                s.settrace()
                print_result(res)
                
        except baseobjspace.OperationError, operationerr:
            if trace_flag:
                res = s.getresult()
                s.settrace()
                print_result(res)

            # XXX insert exception info into the application-level sys.last_xxx
            print
            operationerr.print_detailed_traceback(self.space)

        else:
            print

    def runsource(self, source, ignored_filename = "<input>", symbol = "single"):
        hacked_filename = '<inline>\n' + source
        try:
            code = self.compile(source, hacked_filename, symbol)

        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(self.filename)
            return False

        if code is None:
            return True

        self.runcode(code)
        return False


#//////////////////////////////////////////////////////////////////////////

def trace_interactive(space, banner = None):
    s = space

    # Create an execution context, and set the globals
    ec = s.getexecutioncontext()
    s.w_globals = ec.make_standard_w_globals()
    
    s.setitem(s.w_globals, s.wrap("__name__"), s.wrap("__main__"))
    console = TraceConsole(s)

    if have_readline:
        # Keep here to save windoze tears

        readline.set_completer(Completer(s).complete)
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(25000)

        try:
            readline.read_history_file()

        except IOError:
            pass # guess it doesn't exit 

        import atexit
        atexit.register(readline.write_history_file)

    console.interact(banner)


#//////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':
    from pypy.tool import option
    args = option.process_options(option.get_standard_options(),
                                  option.Options)


    # Create objspace...
    space = option.objspace()
    trace_interactive(space)
    
