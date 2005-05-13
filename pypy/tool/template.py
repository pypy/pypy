import autopath
import sys
import py


def compile_template(source, resultname):
    """Compiles the source code (a py.code.Source or a list/generator of lines)
    which should be a definition for a function named 'resultname'.
    The caller's global dict and local variable bindings are captured.
    """
    if not isinstance(source, py.code.Source):
        lines = list(source)
        lines.append('')
        source = py.code.Source('\n'.join(lines))

    caller = sys._getframe(1)
    locals = caller.f_locals
    localnames = locals.keys()
    localnames.sort()
    values = [locals[key] for key in localnames]
    
    source = source.putaround(
        before = "def container(%s):" % (', '.join(localnames),),
        after  = "# no unindent\n    return %s" % resultname)

    d = {}
    exec source.compile() in caller.f_globals, d
    container = d['container']
    return container(*values)
