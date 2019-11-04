from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef

def make_terminator(space):
    from pypy.module._pypyjson.interp_decoder import Terminator
    return Terminator(space)

def newdictstructure(space, w_list=None):
    from pypy.objspace.std.unicodeobject import W_UnicodeObject
    m = terminator = space.fromcache(make_terminator) # a different one than the one _pypyjson uses
    if w_list is None:
        return m
    for w_x in space.listview(w_list):
        if type(w_x) is not W_UnicodeObject:
            raise oefmt(space.w_TypeError, "expected unicode, got %T", w_x)
        u = space.utf8_w(w_x)
        m = m.get_next(w_x, u, 0, len(u))
        if m is None:
            raise oefmt(space.w_ValueError, "repeated key %R", w_x)
        if not m.is_state_useful():
            m.mark_useful(terminator)  # XXX too aggressive?
    return m




