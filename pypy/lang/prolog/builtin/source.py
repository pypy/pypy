import py
from pypy.lang.prolog.interpreter import arithmetic
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound
from pypy.lang.prolog.builtin.register import expose_builtin


# ___________________________________________________________________
# loading prolog source files

def impl_consult(engine, var):
    import os
    if isinstance(var, term.Atom):
        try:
            fd = os.open(var.name, os.O_RDONLY, 0777)
        except OSError, e:
            error.throw_existence_error("source_sink", var)
            assert 0, "unreachable" # make the flow space happy
        try:
            content = []
            while 1:
                s = os.read(fd, 4096)
                if not s:
                    break
                content.append(s)
            file_content = "".join(content)
        finally:
            os.close(fd)
        engine.runstring(file_content)
expose_builtin(impl_consult, "consult", unwrap_spec=["obj"])


