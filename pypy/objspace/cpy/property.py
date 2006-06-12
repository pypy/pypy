"""
Support to turn GetSetProperty objects into W_Objects containing a
property object of CPython.
"""

from pypy.interpreter.baseobjspace import SpaceCache
from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app
from pypy.interpreter.function import BuiltinFunction
from pypy.objspace.cpy.objspace import W_Object


class PropertyCache(SpaceCache):
    def build(cache, prop):
        space = cache.space

        reslist = []
        for f, arity in [(prop.fget, 1),
                         (prop.fset, 2),
                         (prop.fdel, 1)]:
            if f is None:
                res = None
            else:
                unwrap_spec = [ObjSpace] + [W_Root]*arity
                func = interp2app(prop.fget, unwrap_spec=unwrap_spec)
                func = func.__spacebind__(space)
                bltin = BuiltinFunction(func)
                res = space.wrap(bltin).value
            reslist.append(res)

        # make a CPython property
        p = property(reslist[0], reslist[1], reslist[2], prop.doc)

        w_result = W_Object(p)
        space.wrap_cache[id(w_result)] = w_result, p, follow_annotations
        return w_result


def follow_annotations(bookkeeper, w_property):
    from pypy.annotation import model as annmodel
    p = w_property.value
    for f, arity, key in [(p.fget, 1, 'get'),
                          (p.fset, 2, 'set'),
                          (p.fdel, 1, 'del')]:
        if f is not None:
            s_func = bookkeeper.immutablevalue(f)
            args_s = [annmodel.SomeObject()] * arity
            uniquekey = p, key
            bookkeeper.emulate_pbc_call(uniquekey, s_func, args_s)
