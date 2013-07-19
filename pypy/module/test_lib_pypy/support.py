import py

from pypy.conftest import option
from pypy.interpreter.error import OperationError

def import_lib_pypy(space, name, skipmsg=None):
    """Import a top level module ensuring it's sourced from the lib_pypy
    package.

    Raises a pytest Skip on ImportError if a skip message was specified.
    """
    if option.runappdirect:
        try:
            mod = __import__('lib_pypy.' + name)
        except ImportError as e:
            if skipmsg is not None:
                py.test.skip('%s (%s))' % (skipmsg, str(e)))
            raise
        return getattr(mod, name)

    try:
        # Assume app-level import finds it from the right place (we
        # assert so afterwards). It should as long as a builtin module
        # overshadows it
        w_mod = space.appexec([], "(): import %s; return %s" % (name, name))
    except OperationError as e:
        if skipmsg is not None or not e.match(space, space.w_ImportError):
            raise
        py.test.skip('%s (%s))' % (skipmsg, str(e)))
    w_file = space.getattr(w_mod, space.wrap('__file__'))
    assert space.is_true(space.contains(w_file, space.wrap('lib_pypy'))), \
        ("%s didn't import from lib_pypy. Is a usemodules directive "
         "overshadowing it?" % name)
    return w_mod
