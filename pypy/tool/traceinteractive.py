# Standard imports
import re
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
from pypy.tool.traceop import ResultPrinter

from pypy.interpreter import executioncontext, pyframe, baseobjspace
from pypy.interpreter.baseobjspace import ObjSpace

from pypy.objspace import trace

class Completer:
    """ Stolen mostly from CPython's rlcompleter.py """
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

        w_res = self.space.call_method(self.space.w_globals, "keys")
        namespace_keys = self.space.unwrap(w_res)

        w_res = self.space.call_method(self.space.w_builtins, "keys")
        builtin_keys = self.space.unwrap(w_res)

        matches = []
        n = len(text)

        for l in [namespace_keys, builtin_keys, keyword.kwlist]:
            for word in l:
                if word[:n] == text and word != "__builtins__":
                    matches.append(word)

        return matches

    def attr_matches(self, text):
        m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
        if not m:
            return

        expr, attr = m.group(1, 3)
        s = self.space
        w_obj = s.eval(expr, s.w_globals, s.w_globals)
        words = self.get_words(w_obj)

        w_clz = s.getattr(w_obj, s.wrap("__class__"))
        words += self.get_class_members(w_clz)

        matches = []
        n = len(attr)
        for word in words:
            if word[:n] == attr and word != "__builtins__":
                matches.append("%s.%s" % (expr, word))

        return matches

    def get_words(self, w_clz):
        s = self.space
        w_dir_func = s.getitem(s.w_builtins, s.wrap("dir"))
        w_res = s.call_function(w_dir_func, w_clz)
        return s.unwrap(w_res)

    def get_class_members(self, w_clz):
        s = self.space
        words = self.get_words(w_clz)
        try:                
            w_bases = s.getattr(w_clz, s.wrap("__bases__"))             
            bases_w = s.unpacktuple(w_bases)

        except OperationError:
            return words

        for w_clz in bases_w:
            words += self.get_class_members(w_clz)

        return words

class TraceConsole(code.InteractiveConsole):
    def __init__(self, space):
        code.InteractiveConsole.__init__(self)
        s = self.space = space
        s.setitem(s.w_globals, s.wrap("__pytrace__"), s.wrap(0)) 
        # Trace is binary (on or off), but we have different print levels
        # for tracelevel > 0
        self.tracelevel = 0
        self.resprinter = ResultPrinter()
        
    def interact(self, banner=None):
        if banner is None:
            banner = self.get_banner()
        code.InteractiveConsole.interact(self, banner)

    def get_banner(self):
        banner = "PyPy in %s on top of CPython %s\n%s" % (
            space.__class__.__name__, sys.version.split()[0],
            " [Use  __pytrace__ to set trace level (zero is default and does no tracing)]" )
        return banner

    def raw_input(self, prompt=""):
        # add a character to the PyPy prompt so that you know where you
        # are when you debug it with "python -i py.py"
        try:
            return code.InteractiveConsole.raw_input(self, prompt[0] + prompt)
 
        except KeyboardInterrupt:
            s = self.space
            # fires into an interpreter-level console
            print
            banner = ("Python %s on %s\n" % (sys.version, sys.platform) +
                      "*** Entering interpreter-level console ***")
            local = self.__dict__.copy()
            for w_name in s.unpackiterable(s.w_globals):
                local['w_' + s.unwrap(w_name)] = (
                    s.getitem(s.w_globals, w_name))
            code.interact(banner=banner, local=local)
            # copy back 'w_' names
            for name in local:
                if name.startswith('w_'):
                    s.setitem(s.w_globals,
                              s.wrap(name[2:]),
                              local[name])
            print '*** Leaving interpreter-level console ***'
            raise

    def set_tracelevel(self, tracelevel):
        # Disable tracing altogether?
        if self.tracelevel > 0 and tracelevel == 0:
            self.space.reset_trace()
            print self.get_banner()
            
        if self.tracelevel == 0 and tracelevel > 0:
            trace.create_trace_space(self.space)
            print self.get_banner()

        self.tracelevel = tracelevel

        # XXX Do something better than this - I'm not really sure what is useful
        # and what is (rxe)
        self.resprinter.operations_level = tracelevel

    def runcode(self, code):
        # 'code' is a CPython code object
        from pypy.interpreter.pycode import PyCode
        pycode = PyCode()._from_code(code)

        s = self.space

        try:
            if self.tracelevel:
                s.settrace()
                
            pycode.exec_code(s, s.w_globals, s.w_globals)

            res = None
            if self.tracelevel:
                res = s.getresult()
                
            # Did we modify __pytrace__
            tracelevel = s.unwrap(s.getitem(s.w_globals,
                                            s.wrap("__pytrace__")))
            
            if tracelevel != self.tracelevel:
                self.set_tracelevel(tracelevel)

            if res is not None and self.tracelevel:
                s.settrace()
                self.resprinter.print_result(s, res)
                
        except baseobjspace.OperationError, operationerr:
            if self.tracelevel:
                res = s.getresult()
                s.settrace()
                self.resprinter.print_result(s, res)

            # XXX insert exception info into the application-level sys.last_xxx
            print
            operationerr.print_application_traceback(self.space)

        else:
            print

    def runsource(self, source, ignored_filename = "<input>", symbol = "single"):
        hacked_filename = '<inline> ' + source[:80] + "..."
        hacked_filename = hacked_filename.replace("\n", r"\n")
        try:
            code = self.compile(source, hacked_filename, symbol)

        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(self.filename)
            return False

        if code is None:
            return True

        self.runcode(code)
        return False

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
    
if __name__ == '__main__':
    
    from pypy.tool import option
    args = option.process_options(option.get_standard_options(),
                                  option.Options)

    # Create objspace...
    space = option.objspace()
    trace_interactive(space)
