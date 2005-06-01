from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomePBC, SomeInstance
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import inputconst


#
#  There is one "vtable" per user class, with the following structure:
#  A root class "object" has:
#
#      struct object_vtable {
#          struct object_vtable* parenttypeptr;
#      }
#
#  Every other class X, with parent Y, has the structure:
#
#      struct vtable_X {
#          struct vtable_Y super;   // inlined
#          ...                      // extra class attributes
#      }

# The type of the instances is:
#
#     struct object {       // for the root class
#         struct object_vtable* typeptr;
#     }
#
#     struct X {
#         struct Y super;   // inlined
#         ...               // extra instance attributes
#     }
#

OBJECT_VTABLE = ForwardReference()
TYPEPTR = NonGcPtr(OBJECT_VTABLE)
OBJECT_VTABLE.become(Struct('object_vtable', ('parenttypeptr', TYPEPTR)))

OBJECT = GcStruct('object', ('typeptr', TYPEPTR))


class RClassDef:

    def __init__(self, classdef):
        self.classdef = classdef
        if classdef.basedef is None:
            self.depth = 1
            parent_vtable_type = OBJECT_VTABLE
            parent_typeptr = nullptr(OBJECT_VTABLE)
            parent_object_type = OBJECT
        else:
            rbasedef = getrclassdef(classdef.basedef)
            self.depth = rbasedef.depth + 1
            parent_vtable_type = rbasedef.vtable_type
            parent_typeptr = rbasedef.typeptr
            parent_object_type = rbasedef.object_type
        self.vtable_type = Struct('%s_vtable' % classdef.cls.__name__,
                                  ('super', parent_vtable_type),
                                  # XXX class attributes
                                  )
        self.vtable = malloc(self.vtable_type, immortal=True)
        # cast the vtable pointer from "vtable_type" to "parent_vtable_type"
        # to "parent_parent_vtable_type" to .... to OBJECT_VTABLE
        p = self.vtable
        for i in range(self.depth):
            p = p.super
        self.typeptr = cast_flags(TYPEPTR, p)
        p.parenttypeptr = parent_typeptr
        #
        self.parent_object_type = parent_object_type
        self.object_type = GcStruct(classdef.cls.__name__,
                                    ('super', parent_object_type),
                                    # XXX instance attributes
                                    )

    def parent_cast(self, targetclassdef, v, llops):
        classdef = self.classdef
        super_name = inputconst(Void, "super")
        while classdef is not targetclassdef:
            rclassdef = getrclassdef(classdef)
            parent_object_type = rclassdef.parent_object_type
            v = llops.genop('getsubstruct', [v, super_name],
                            resulttype = GcPtr(parent_object_type))
            classdef = classdef.basedef
        return v

    def rtype_new_instance(self, llops):
        ctype = inputconst(Void, self.object_type)
        vptr = llops.genop('malloc', [ctype],
                           resulttype = GcPtr(self.object_type))
        vptr_as_object = self.parent_cast(None, vptr, llops)
        typeptr_name = inputconst(Void, "typeptr")
        ctypeptr = inputconst(TYPEPTR, self.typeptr)
        llops.genop('setfield', [vptr_as_object, typeptr_name, ctypeptr])
        # XXX call __init__ somewhere
        return vptr


def getrclassdef(classdef):
    try:
        return classdef._rtype_rclassdef_
    except AttributeError:
        classdef._rtype_rclassdef_ = result = RClassDef(classdef)
        return result


def rtype_new_instance(s_cls, hop):
    assert s_cls.is_constant()
    cls = s_cls.const
    classdef = hop.rtyper.annotator.getuserclasses()[cls]
    rclassdef = getrclassdef(classdef)
    return rclassdef.rtype_new_instance(hop.llops)


# ____________________________________________________________

class __extend__(SomeInstance):

    def lowleveltype(s_ins):
        rclassdef = getrclassdef(s_ins.classdef)
        return GcPtr(rclassdef.object_type)

    def rtype_type(s_ins, hop):
        rclassdef = getrclassdef(s_ins.classdef)
        vptr, = hop.inputargs(s_ins)
        vptr_as_object = rclassdef.parent_cast(None, vptr, hop.llops)
        typeptr_name = inputconst(Void, "typeptr")
        return hop.genop('getfield', [vptr_as_object, typeptr_name],
                         resulttype=TYPEPTR)
