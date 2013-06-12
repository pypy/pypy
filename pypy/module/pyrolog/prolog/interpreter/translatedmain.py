import os, sys
from rpython.rlib.parsing.parsing import ParseError
from rpython.rlib.parsing.deterministic import LexerError
from prolog.interpreter.parsing import parse_file, get_query_and_vars
from prolog.interpreter.parsing import get_engine
from prolog.interpreter.continuation import Continuation, Engine, \
        DoneSuccessContinuation, DoneFailureContinuation
from prolog.interpreter import error, term
import prolog.interpreter.term
prolog.interpreter.term.DEBUG = False

helptext = """
 ';':   redo
 'p':   print
 'h':   help
 
"""

class StopItNow(Exception):
    pass

class ContinueContinuation(Continuation):
    def __init__(self, engine, var_to_pos, write):
        Continuation.__init__(self, engine, DoneSuccessContinuation(engine))
        self.var_to_pos = var_to_pos
        self.write = write

    def activate(self, fcont, heap):
        self.write("yes\n")
        var_representation(self.var_to_pos, self.engine, self.write, heap)
        while 1:
            if isinstance(fcont, DoneFailureContinuation):
                self.write("\n")
                return DoneSuccessContinuation(self.engine), fcont, heap
            res = getch()
            if res in "\r\x04\n":
                self.write("\n")
                raise StopItNow()
            if res in ";nr":
                raise error.UnificationFailed
            elif res in "h?":
                self.write(helptext)
            elif res in "p":
                var_representation(self.var_to_pos, self.engine, self.write, heap)
            else:
                self.write('unknown action. press "h" for help\n')
                
def var_representation(var_to_pos, engine, write, heap):
    from prolog.builtin import formatting
    f = formatting.TermFormatter(engine, quoted=True, max_depth=20)
    for var, real_var in var_to_pos.iteritems():
        if var.startswith("_"):
            continue
        value = real_var.dereference(heap)
        val = f.format(value)
        if isinstance(value, term.AttVar):
            write("%s\n" % val)
        else:
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

def run(query, var_to_pos, engine):
    from prolog.builtin import formatting
    f = formatting.TermFormatter(engine, quoted=True, max_depth=20)
    try:
        if query is None:
            return
        engine.run(query, engine.modulewrapper.current_module, 
                ContinueContinuation(engine, var_to_pos, printmessage))
    except error.UnificationFailed:
        printmessage("no\n")
    except (error.UncaughtError, error.CatchableError), e:
        f._make_reverse_op_mapping()
        printmessage("ERROR: ")
        t = e.term
        if isinstance(t, term.Callable):
            errorterm = t.argument_at(0)
            if isinstance(errorterm, term.Callable):
                if errorterm.name() == "instantiation_error":
                    printmessage("arguments not sufficiently instantiated\n")
                    return
                elif errorterm.name()== "existence_error":
                    if isinstance(errorterm, term.Callable):
                        printmessage("Undefined %s: %s\n" % (
                            f.format(errorterm.argument_at(0)),
                            f.format(errorterm.argument_at(1))))
                        return
                elif errorterm.name()== "domain_error":
                    if isinstance(errorterm, term.Callable):
                        printmessage(
                            "Domain error: '%s' expected, found '%s'\n" % (
                            f.format(errorterm.argument_at(0)),
                            f.format(errorterm.argument_at(1))))
                        return
                elif errorterm.name()== "type_error":
                    if isinstance(errorterm, term.Callable):
                        printmessage(
                            "Type error: '%s' expected, found '%s'\n" % (
                            f.format(errorterm.argument_at(0)),
                            f.format(errorterm.argument_at(1))))
                        return
                elif errorterm.name() == "syntax_error":
                    if isinstance(errorterm, term.Callable):    
                        printmessage("Syntax error: '%s'\n" % \
                        f.format(errorterm.argument_at(0)))
                        return
                elif errorterm.name() == "permission_error":
                    if isinstance(errorterm, term.Callable):    
                        printmessage("Permission error: '%s', '%s', '%s'\n" % (
                        f.format(errorterm.argument_at(0)),
                        f.format(errorterm.argument_at(1)),
                        f.format(errorterm.argument_at(2))))
                        return
                elif errorterm.name() == "representation_error":
                    if isinstance(errorterm, term.Callable):
                        printmessage("%s: Cannot represent: %s\n" % (
                        f.format(errorterm.argument_at(0)),
                        f.format(errorterm.argument_at(1))))
                        return
                elif errorterm.name() == "import_error":
                    if isinstance(errorterm, term.Callable):
                        printmessage("Exported procedure %s:%s is not defined\n" % (
                        f.format(errorterm.argument_at(0)),
                        f.format(errorterm.argument_at(1))))
                        return

    # except error.UncatchableError, e:
    #     printmessage("INTERNAL ERROR: %s\n" % (e.message, ))
    except StopItNow:
        printmessage("yes\n")

def repl(engine):
    printmessage("welcome!\n")
    while 1:
        module = engine.modulewrapper.current_module.name
        if module == "user":
            module = ""
        else:
            module += ":  "
        printmessage(module + ">?- ")
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
    e.run(term.Callable.build("consult", [term.Callable.build(filename)]),
            e.modulewrapper.user_module)

if __name__ == '__main__':
    from sys import argv
    e = Engine(load_system=True)
    if len(argv) == 2:
        execute(e, argv[1])
    repl(e)
