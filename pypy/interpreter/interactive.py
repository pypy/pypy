import autopath

from pypy.interpreter import error
from pypy.interpreter import executioncontext, baseobjspace, module, main
import sys
import code
import time


class Completer:
    """ Stolen mostly from CPython's rlcompleter.py """
    def __init__(self, space, w_globals):
        self.space = space
        self.w_globals = w_globals

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
        import keyword
        w_res = self.space.call_method(self.w_globals, "keys")
        namespace_keys = self.space.unwrap(w_res)
        w_res = self.space.call_method(self.space.builtin.getdict(), "keys")
        builtin_keys = self.space.unwrap(w_res)
        
        matches = []
        n = len(text)

        for l in [namespace_keys, builtin_keys, keyword.kwlist]:
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
        w_obj = s.eval(expr, self.w_globals, self.w_globals)
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
        w_dir_func = s.builtin.get("dir")
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

class PyPyConsole(code.InteractiveConsole):
    def __init__(self, objspace, verbose=0, completer=False):
        code.InteractiveConsole.__init__(self)
        self.space = objspace
        self.verbose = verbose
        self.ec = executioncontext.ExecutionContext(self.space)

        space=self.space

        mainmodule = main.ensure__main__(space)
        self.w_globals = mainmodule.w_dict
        space.setitem(self.w_globals, space.wrap('__builtins__'), space.builtin)
        if completer:
            self.enable_command_line_completer()
        # XXX check: do we need self.ec, self.w_globals?

        space.exec_("__pytrace__ = 0", self.w_globals, self.w_globals) 
        self.tracelevel = 0

    def enable_command_line_completer(self):
        try:
            import readline
            # Keep here to save windoze tears
            readline.set_completer(Completer(self.space, self.w_globals).complete)
            readline.parse_and_bind("tab: complete")
            readline.set_history_length(25000)

            try:
                readline.read_history_file()
            except IOError:
                pass # guess it doesn't exit 

            import atexit
            atexit.register(readline.write_history_file)
        except:
            pass

    def interact(self, banner=None):
        #banner = "Python %s in pypy\n%s / %s" % (
        #    sys.version, self.__class__.__name__,
        #    self.space.__class__.__name__)
        elapsed = time.time() - self.space._starttime
        banner = "PyPy in %s on top of Python %s (startupttime: %.2f secs)" % (
            self.space.__repr__(), sys.version.split()[0], elapsed)
        code.InteractiveConsole.interact(self, banner)

    def raw_input(self, prompt=""):
        # add a character to the PyPy prompt so that you know where you
        # are when you debug it with "python -i py.py"
        try:
            return code.InteractiveConsole.raw_input(self, prompt[0] + prompt)
        except KeyboardInterrupt:
            # fires into an interpreter-level console
            print
            banner = ("Python %s on %s\n" % (sys.version, sys.platform) +
                      "*** Entering interpreter-level console ***")
            local = self.__dict__.copy()
            for w_name in self.space.unpackiterable(self.w_globals):
                local['w_' + self.space.str_w(w_name)] = (
                    self.space.getitem(self.w_globals, w_name))
            code.interact(banner=banner, local=local)
            # copy back 'w_' names
            for name in local:
                if name.startswith('w_'):
                    self.space.setitem(self.w_globals,
                                       self.space.wrap(name[2:]),
                                       local[name])
            print '*** Leaving interpreter-level console ***'
            raise

    def runcode(self, code):
        # 'code' is a CPython code object
        from pypy.interpreter.pycode import PyCode
        pycode = PyCode(self.space)._from_code(code)
        try:
            self.settrace()
            pycode.exec_code(self.space, self.w_globals, self.w_globals)
            self.checktrace()
            
        except error.OperationError, operationerr:
            space = self.space
            try:
                if operationerr.match(space, space.w_SystemExit):
                    w_exitcode = space.getattr(operationerr.w_value,
                                               space.wrap('code'))
                    if space.is_w(w_exitcode, space.w_None):
                        exitcode = 0
                    else:
                        try:
                            exitcode = space.int_w(w_exitcode)
                        except error.OperationError:
                            # not an integer: print it to stderr
                            msg = space.str_w(space.str(w_exitcode))
                            print >> sys.stderr, msg
                            exitcode = 1
                    raise SystemExit(exitcode)
                space.setitem(space.sys.w_dict, space.wrap('last_type'),
                              operationerr.w_type)
                space.setitem(space.sys.w_dict, space.wrap('last_value'),
                              operationerr.w_value)
                space.setitem(space.sys.w_dict, space.wrap('last_traceback'),
                              space.wrap(operationerr.application_traceback))
            except error.OperationError, operationerr:
                pass   # let the code below print any error we get above
            if self.verbose:
                operationerr.print_detailed_traceback(space)
            else:
                operationerr.print_application_traceback(space)
            # for debugging convenience we also insert the exception into
            # the interpreter-level sys.last_xxx
            sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()
        else:
            try:
                if sys.stdout.softspace:
                    print
            except AttributeError:
                # Don't crash if user defined stdout doesn't have softspace
                pass

    def runsource(self, source, ignored_filename="<input>", symbol="single"):
        hacked_filename = '<inline>' + source
        try:
            code = self.compile(source, hacked_filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(self.filename)
            return 0
        if code is None:
            return 1
        self.runcode(code)
        return 0

    def settrace(self):
        if self.tracelevel:
            self.space.settrace()

    def checktrace(self):
        from pypy.objspace import trace

        s = self.space

        # Did we modify __pytrace__
        tracelevel = s.int_w(s.getitem(self.w_globals,
                                       s.wrap("__pytrace__")))

        if self.tracelevel > 0 and tracelevel == 0:
            s.reset_trace()
            print "Tracing disabled"
            
        if self.tracelevel == 0 and tracelevel > 0:
            trace.create_trace_space(s)
            print "Tracing enabled"

        self.tracelevel = tracelevel

    def set_tracelevel(self, tracelevel):
        # Disable tracing altogether?
        from pypy.objspace import trace

        if self.tracelevel > 0 and tracelevel == 0:
            self.space.reset_trace()
            print self.get_banner()
            
        if self.tracelevel == 0 and tracelevel > 0:
            trace.create_trace_space(self.space)
            print self.get_banner()

        self.tracelevel = tracelevel

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
