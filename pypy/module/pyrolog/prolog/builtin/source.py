import py
from prolog.interpreter import helper, term, error
from prolog.builtin.register import expose_builtin
from prolog.builtin.sourcehelper import get_source


# ___________________________________________________________________
# loading prolog source files

@expose_builtin("consult", unwrap_spec=["obj"])
def impl_consult(engine, heap, var):
    if isinstance(var, term.Atom):
        file_content = get_source(var.name())
        engine.runstring(file_content)
