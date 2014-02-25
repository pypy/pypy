from pypy.interpreter import baseobjspace
from pypy.interpreter.typedef import TypeDef, GetSetProperty, Member
from pypy.interpreter.typedef import descr_get_dict, descr_set_dict
from pypy.interpreter.typedef import descr_del_dict
from pypy.interpreter.baseobjspace import SpaceCache
from rpython.rlib import jit

__all__ = ['StdTypeDef']


class StdTypeDef(TypeDef):

    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only."
        TypeDef.__init__(self, __name, __base, **rawdict)
        self.any = type("W_Any"+__name.title(), (baseobjspace.W_Root,), {'typedef': self})

@jit.unroll_safe
def issubtypedef(a, b):
    from pypy.objspace.std.objectobject import W_ObjectObject
    if b is W_ObjectObject.typedef:
        return True
    if a is None:
        return False
    if a is b:
        return True
    for a1 in a.bases:
        if issubtypedef(a1, b):
            return True
    return False

std_dict_descr = GetSetProperty(descr_get_dict, descr_set_dict, descr_del_dict,
                    doc="dictionary for instance variables (if defined)")
std_dict_descr.name = '__dict__'

# ____________________________________________________________
#
# All the code below fishes from the multimethod registration tables
# the descriptors to put into the W_TypeObjects.
#

class TypeCache(SpaceCache):
    def build(cache, typedef):
        "NOT_RPYTHON: initialization-time only."
        # build a W_TypeObject from this StdTypeDef
        from pypy.objspace.std.typeobject import W_TypeObject
        from pypy.objspace.std.objectobject import W_ObjectObject

        space = cache.space
        w = space.wrap
        rawdict = typedef.rawdict
        lazyloaders = {}

        # compute the bases
        if typedef is W_ObjectObject.typedef:
            bases_w = []
        else:
            bases = typedef.bases or [W_ObjectObject.typedef]
            bases_w = [space.gettypeobject(base) for base in bases]

        # wrap everything
        dict_w = {}
        for descrname, descrvalue in rawdict.items():
            dict_w[descrname] = w(descrvalue)

        if typedef.applevel_subclasses_base is not None:
            overridetypedef = typedef.applevel_subclasses_base.typedef
        else:
            overridetypedef = typedef
        w_type = W_TypeObject(space, typedef.name, bases_w, dict_w,
                              overridetypedef=overridetypedef)
        if typedef is not overridetypedef:
            w_type.w_doc = space.wrap(typedef.doc)
        w_type.lazyloaders = lazyloaders
        return w_type

    def ready(self, w_type):
        w_type.ready()
