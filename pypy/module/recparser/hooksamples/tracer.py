"""this one logs simple assignments and somewhat clearly shows
that we need a nice API to define "joinpoints". Maybe a SAX-like
(i.e. event-based) API ?

XXX: crashes on everything else than simple assignment (AssAttr, etc.)
"""

from parser import ASTPrintnl, ASTConst, ASTName, ASTAssign, ASTMutator
from parser import install_compiler_hook, source2ast

BEFORE_LOG_SOURCE = """if '%s' in locals() or '%s' in globals():
    print '(before) %s <--', locals().get('%s', globals().get('%s', '<XXX>'))
"""
AFTER_LOG_SOURCE = "print '(after) %s <--', %s"

def get_statements(source):
    module = source2ast(source)
    return module.node.nodes

class Tracer(ASTMutator):
    def visitAssName(self, assname):
        assign = assname
        while not isinstance(assign, ASTAssign):
            assign = assign.parent
        stmt = assign.parent
        varname = assname.name
        before_stmts = get_statements(BEFORE_LOG_SOURCE % ((varname,) * 5))
        after_stmts = get_statements(AFTER_LOG_SOURCE % (varname, varname))
        stmt.insert_before(assign, before_stmts)
        stmt.insert_after(assign, after_stmts)
        return assname


def _trace(ast, enc, filename):
    return ast.accept(Tracer())

install_compiler_hook(_trace)


code = """
a = 3
b = 2
a = 1
"""
exec code
