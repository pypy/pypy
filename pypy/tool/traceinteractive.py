# Python imports
import sys
import code
import repr
import keyword
import linecache

try:
    import readline
    import rlcompleter
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

# Global
operations = dict([(r[0], r[0]) for r in ObjSpace.MethodTable])


#//////////////////////////////////////////////////////////////////////////

if have_readline:
    class Completer(rlcompleter.Completer):
        # TODO Tailor this for own means

        def __init__(self, objspace):
            self.objspace = objspace
            

        # Very frustratingly, we have a lot of duplication of rlcompleter here
        def global_matches(self, text):
            print "GERE"
            locals = self.objspace.unwrap(self.objspace.w_locals)
            matches = []
            n = len(text)
            for l in [locals.keys(), __builtin__.__dict__.keys(), keyword.kwlist]:
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
            object = self.locals[expr]
            words = dir(object)
            if hasattr(object, '__class__'):
                words.append('__class__')
                words = words + self.get_class_members(object.__class__)

            matches = []
            n = len(attr)
            for word in words:

                if word[:n] == attr and word != "__builtins__":
                    matches.append("%s.%s" % (expr, word))
            return matches

        def get_class_members(self, klass):
            ret = dir(klass)
            if hasattr(klass, '__bases__'):
                for base in klass.__bases__:
                    ret = ret + self.get_class_members(base)
            return ret


#//////////////////////////////////////////////////////////////////////////

class TraceConsole(code.InteractiveConsole):
    def __init__(self, objspace):
        code.InteractiveConsole.__init__(self)
        s = self.space = trace.TraceObjSpace(objspace)
        s.setitem(s.w_globals, s.wrap("__pytrace__"), s.w_True)
        self.objspacename = objspace.__class__.__name__


    def interact(self, banner=None):
        if banner is None:
            banner = "Python %s in pypy(trace)\n%s / %s - %s" % (
                sys.version, self.__class__.__name__,
                self.objspacename,
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
        try:
            s = self.space
            trace_flag = s.unwrap(s.getitem(s.w_globals,
                                            s.wrap("__pytrace__")))
            if trace_flag:
                s.settrace()

            pycode.exec_code(s, s.w_globals, s.w_globals)
            if trace_flag:
                res = s.getresult()
                s.settrace()
                print_result(res)
        
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




def trace_interactive(objspace, banner = None):
    s = objspace

    ec = s.getexecutioncontext()
    s.w_globals = ec.make_standard_w_globals()
    s.setitem(s.w_globals, s.wrap("__name__"), s.wrap("__main__"))
    console = TraceConsole(s)
    if have_readline:
        # Keep here to save windoze tears
        readline.set_completer(Completer(s).complete)
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(25000)
        readline.read_history_file()

        import atexit
        atexit.register(readline.write_history_file)

    console.interact(banner)


if __name__ == '__main__':

    from pypy.tool import option
    from pypy.tool import testit
    args = option.process_options(option.get_standard_options(),
                                  option.Options)


    # Create objspace...
    objspace = option.objspace()
    trace_interactive(objspace)
    
