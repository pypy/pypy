#!/usr/bin/env python

try:
    import autopath
except ImportError:
    pass

import py
import sys
#sys.path.append(str(py.magic.autopath().dirpath().dirpath()))

from pypy.rlib.parsing.parsing import ParseError
from pypy.rlib.parsing.deterministic import LexerError
from pypy.lang.prolog.interpreter.parsing import parse_file, get_query_and_vars
from pypy.lang.prolog.interpreter.parsing import get_engine
from pypy.lang.prolog.interpreter.engine import Engine
from pypy.lang.prolog.interpreter.engine import Continuation
from pypy.lang.prolog.interpreter import error
import pypy.lang.prolog.interpreter.term
pypy.lang.prolog.interpreter.term.DEBUG = False

import code

helptext = """
 ';':   redo
 'p':   print
 'h':   help
 
"""

class StopItNow(Exception):
    pass

class ContinueContinuation(Continuation):
    def __init__(self, var_to_pos, write):
        self.var_to_pos = var_to_pos
        self.write = write

    def _call(self, engine):
        self.write("yes\n")
        var_representation(self.var_to_pos, engine, self.write)
        while 1:
            res = getch()
            self.write(res+"\n")
            if res in "\r\x04":
                self.write("\n")
                raise StopItNow()
            if res in ";nr":
                raise error.UnificationFailed
            elif res in "h?":
                self.write(helptext)
            elif res in "p":
                var_representation(self.var_to_pos, engine, self.write)
            else:
                self.write('unknown action. press "h" for help\n')

def var_representation(var_to_pos, engine, write):
    from pypy.lang.prolog.builtin.formatting import TermFormatter
    f = TermFormatter(engine, quoted=True, max_depth=10)
    vars = var_to_pos.items()
    vars.sort()
    heap = engine.heap
    for var, real_var in vars:
        if var.startswith("_"):
            continue
        val = real_var.getvalue(heap)
        write("%s = %s\n" % (var, f.format(val)))

class PrologConsole(code.InteractiveConsole):
    def __init__(self, engine):
        code.InteractiveConsole.__init__(self, {})
        del self.__dict__['compile']
        self.engine = engine

    def compile(self, source, filename="<input>", symbol="single"):
        try:
            if not source.strip():
                return None, None
            return get_query_and_vars(source)
        except ParseError, exc:
            self.write(exc.nice_error_message("<stdin>", source) + "\n")
            raise SyntaxError
        except LexerError, exc:
            self.write(exc.nice_error_message("<stdin>") + "\n")
            raise SyntaxError

    def runcode(self, code):
        try:
            query, var_to_pos = code
            if query is None:
                return
            self.engine.run(query, ContinueContinuation(var_to_pos, self.write))
        except error.UnificationFailed:
            self.write("no\n")
        except error.CatchableError, e:
            self.write("ERROR: ")
            if e.term.args[0].name == "instantiation_error":
                print e.term
                self.write("arguments not sufficiently instantiated\n")
            elif e.term.args[0].name == "existence_error":
                print e.term
                self.write("Undefined %s: %s\n" % (e.term.args[0].args[0],
                                                   e.term.args[0].args[1]))
            else:
                self.write("of unknown type: %s\n" % (e.term, ))
        except error.UncatchableError, e:
            self.write("INTERNAL ERROR: %s\n" % (e.message, ))
        except StopItNow:
            self.write("yes\n")

    def showtracebach(self):
        self.write("traceback. boooring. nothing to see here")


class _Getch(object):
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            import msvcrt
            self.impl = self.get_windows
        except ImportError:
            try:
                import tty, sys, termios
                self.impl = self.get_unix
            except ImportError:
                import Carbon, Carbon.Evt
                self.impl = self.get_carbon

    def __call__(self):
        return self.impl()

    def get_unix(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def get_windows(self):
        import msvcrt
        return msvcrt.getch()


    def get_carbon(self):
        """
        A function which returns the current ASCII key that is down;
        if no ASCII key is down, the null string is returned.  The
        page http://www.mactech.com/macintosh-c/chap02-1.html was
        very helpful in figuring out how to do this.
        """
        import Carbon
        if Carbon.Evt.EventAvail(0x0008)[0]==0: # 0x0008 is the keyDownMask
            return ''
        else:
            # The message (msg) contains the ASCII char which is
            # extracted with the 0x000000FF charCodeMask; this
            # number is converted to an ASCII character with chr() and
            # returned
            (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            return chr(msg & 0x000000FF)


getch = _Getch()


def main():
    import readline
    oldps1 = getattr(sys, "ps1", ">>> ")
    oldps2 = getattr(sys, "ps2", "... ")
    try:
        sys.ps1 = ">?- "
        sys.ps2 = "... "
        if not len(sys.argv) == 2:
            e = Engine()
        else:
            try:
                source = py.path.local(sys.argv[1]).read()
                e = get_engine(source)
            except ParseError, exc:
                print exc.nice_error_message("<stdin>", source) + "\n"
                sys.exit(1)
            except LexerError, exc:
                print exc.nice_error_message("<stdin>") + "\n"
                sys.exit(1)
        c = PrologConsole(e)
        c.interact("PyPy Prolog Console")
    finally:
        sys.ps1 = oldps1
        sys.ps2 = oldps2
    

if __name__ == '__main__':
    main()
