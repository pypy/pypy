from pypy.interpreter import error
from pypy.interpreter import baseobjspace, module, main
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
            bases_w = s.fixedview(w_bases)

        except error.OperationError:
            return words

        for w_clz in bases_w:
            words += self.get_class_members(w_clz)

        return words

class PyPyConsole(code.InteractiveConsole):
    def __init__(self, objspace, verbose=0, completer=False):
        code.InteractiveConsole.__init__(self)
        self.space = objspace
        self.verbose = verbose
        space = self.space
        self.console_compiler_flags = 0

        mainmodule = main.ensure__main__(space)
        self.w_globals = mainmodule.w_dict
        space.setitem(self.w_globals, space.wrap('__builtins__'), space.builtin)
        if completer:
            self.enable_command_line_completer()

        # forbidden:
        #space.exec_("__pytrace__ = 0", self.w_globals, self.w_globals)
        space.setitem(self.w_globals, space.wrap('__pytrace__'),space.wrap(0))
        self.tracelevel = 0
        self.console_locals = {}

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
        w_sys = self.space.sys
        major, minor, micro, _, _ = self.space.unwrap(self.space.sys.get('pypy_version_info'))
        elapsed = time.time() - self.space._starttime
        banner = "PyPy %d.%d.%d in %r on top of Python %s (startuptime: %.2f secs)" % (
            major, minor, micro, self.space, sys.version.split()[0], elapsed)
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
            local = self.console_locals
            # don't copy attributes that look like names that came
            # from self.w_globals (itself the main offender) as they
            # would then get copied back into the applevel namespace.
            local.update(dict([(k,v) for (k, v) in self.__dict__.iteritems()
                               if not k.startswith('w_')]))
            del local['locals']
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
        raise NotImplementedError

    def runsource(self, source, ignored_filename="<input>", symbol="single"):
        # the following hacked file name is recognized specially by error.py
        hacked_filename = '<inline>\n' + source
        compiler = self.space.getexecutioncontext().compiler

        # CPython 2.6 turns console input into unicode
        if isinstance(source, unicode):
            source = source.encode(sys.stdin.encoding)

        def doit():
            # compile the provided input
            code = compiler.compile_command(source, hacked_filename, symbol,
                                            self.console_compiler_flags)
            if code is None:
                raise IncompleteInput
            self.console_compiler_flags |= compiler.getcodeflags(code)

            # execute it
            self.settrace()
            try:
                code.exec_code(self.space, self.w_globals, self.w_globals)
            finally:
                if self.tracelevel:
                    self.space.unsettrace()
            self.checktrace()

        # run doit() in an exception-catching box
        try:
            main.run_toplevel(self.space, doit, verbose=self.verbose)
        except IncompleteInput:
            return 1
        else:
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
            self.space.unsettrace()
            print "Tracing enabled"
                        
        self.tracelevel = tracelevel


class IncompleteInput(Exception):
    pass

