import os, sys
from pypy.rlib.parsing.parsing import ParseError
from pypy.rlib.parsing.deterministic import LexerError
from pypy.lang.prolog.interpreter.interactive import helptext
from pypy.lang.prolog.interpreter.parsing import parse_file, get_query_and_vars
from pypy.lang.prolog.interpreter.parsing import get_engine
from pypy.lang.prolog.interpreter.engine import Engine
from pypy.lang.prolog.interpreter.engine import Continuation
from pypy.lang.prolog.interpreter import error, term
import pypy.lang.prolog.interpreter.term
pypy.lang.prolog.interpreter.term.DEBUG = False


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
            #self.write(res+"\n")
            if res in "\r\x04\n":
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
    from pypy.lang.prolog.builtin import formatting
    f = formatting.TermFormatter(engine, quoted=True, max_depth=20)
    for var, real_var in var_to_pos.iteritems():
        if var.startswith("_"):
            continue
        val = f.format(real_var.getvalue(engine.heap))
        write("%s = %s\n" % (var, val))

def getch():
    line = readline()
    return line[0]

def debug(msg):
    os.write(2, "debug: " + msg + '\n')

def printmessage(msg):
    os.write(1, msg)

def readline():
    result = []
    while 1:
        s = os.read(0, 1)
        result.append(s)
        if s == "\n":
            break
        if s == '':
            if len(result) > 1:
                break
            raise SystemExit
    return "".join(result)

def run(goal, var_to_pos, e):
    from pypy.lang.prolog.interpreter.error import UnificationFailed, CatchableError
    from pypy.lang.prolog.interpreter.error import UncatchableError, UserError
    from pypy.lang.prolog.builtin import formatting
    f = formatting.TermFormatter(e, quoted=True, max_depth=20)
    try:
        e.run(goal, ContinueContinuation(var_to_pos, printmessage))
    except UnificationFailed:
        printmessage("no\n")
    except UncatchableError, e:
        printmessage("INTERNAL ERROR: %s\n" % (e.message, ))
    except UserError, e:
        printmessage("ERROR: ")
        f._make_reverse_op_mapping()
        printmessage("Unhandled exception: ")
        printmessage(f.format(e.term))
    except CatchableError, e:
        f._make_reverse_op_mapping()
        printmessage("ERROR: ")
        t = e.term
        if isinstance(t, term.Term):
            errorterm = t.args[0]
            if isinstance(errorterm, term.Callable):
                if errorterm.name == "instantiation_error":
                    printmessage("arguments not sufficiently instantiated\n")
                    return
                elif errorterm.name == "existence_error":
                    if isinstance(errorterm, term.Term):
                        printmessage("Undefined %s: %s\n" % (
                            f.format(errorterm.args[0]),
                            f.format(errorterm.args[1])))
                        return
                elif errorterm.name == "domain_error":
                    if isinstance(errorterm, term.Term):
                        printmessage(
                            "Domain error: '%s' expected, found '%s'\n" % (
                            f.format(errorterm.args[0]),
                            f.format(errorterm.args[1])))
                        return
                elif errorterm.name == "type_error":
                    if isinstance(errorterm, term.Term):
                        printmessage(
                            "Type error: '%s' expected, found '%s'\n" % (
                            f.format(errorterm.args[0]),
                            f.format(errorterm.args[1])))
                        return
        printmessage(" (but I cannot tell you which one)\n")
    except StopItNow:
        pass
    else:
        printmessage("yes\n")

def repl(engine):
    printmessage("welcome!\n")
    while 1:
        printmessage(">?- ")
        line = readline()
        if line == "halt.\n":
            break
        try:
            goals, var_to_pos = engine.parse(line)
        except ParseError, exc:
            printmessage(exc.nice_error_message("<stdin>", line) + "\n")
            continue
        except LexerError, exc:
            printmessage(exc.nice_error_message("<stdin>") + "\n")
            continue
        for goal in goals:
            run(goal, var_to_pos, engine)
 
def execute(e, filename):
    e.run(term.Term("consult", [term.Atom(filename)]))

if __name__ == '__main__':
    e = Engine()
    repl(e)
