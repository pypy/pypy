from pypy.rpython.rmodel import inputconst, log
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rclass import AbstractInstanceRepr, FieldListAccessor


class AbstractVirtualizable2InstanceRepr(AbstractInstanceRepr):

    def _super(self):
        return super(AbstractVirtualizable2InstanceRepr, self)

    def __init__(self, rtyper, classdef):
        self._super().__init__(rtyper, classdef)
        classdesc = classdef.classdesc
        if '_virtualizable2_' in classdesc.classdict:
            basedesc = classdesc.basedesc
            assert basedesc is None or basedesc.lookup('_virtualizable2_') is None
            self.top_of_virtualizable_hierarchy = True
            self.accessor = FieldListAccessor()
        else:
            self.top_of_virtualizable_hierarchy = False

    def _setup_repr_llfields(self):
        raise NotImplementedError

    def set_vable(self, llops, vinst, force_cast=False):
        raise NotImplementedError

    def _setup_repr(self):
        if self.top_of_virtualizable_hierarchy:
            hints = {'virtualizable2_accessor': self.accessor}
            llfields = self._setup_repr_llfields()
            if llfields:
                self._super()._setup_repr(llfields, hints = hints)
            else:
                self._super()._setup_repr(hints = hints)
            c_vfields = self.classdef.classdesc.classdict['_virtualizable2_']
            self.my_redirected_fields = self._parse_field_list(c_vfields.value,
                                                               self.accessor)
        else:
            self._super()._setup_repr()
            # ootype needs my_redirected_fields even for subclass. lltype does
            # not need it, but it doesn't hurt to have it anyway
            self.my_redirected_fields = self.rbase.my_redirected_fields

    def new_instance(self, llops, classcallhop=None):
        vptr = self._super().new_instance(llops, classcallhop)
        self.set_vable(llops, vptr)
        return vptr

    def hook_access_field(self, vinst, cname, llops, flags):
        #if not flags.get('access_directly'):
        if self.my_redirected_fields.get(cname.value):
            cflags = inputconst(lltype.Void, flags)
            llops.genop('jit_force_virtualizable', [vinst, cname, cflags])


def replace_force_virtualizable_with_call(graphs, VTYPEPTR, funcptr):
    # funcptr should be an ll or oo function pointer with a VTYPEPTR argument
    c_funcptr = inputconst(lltype.typeOf(funcptr), funcptr)
    count = 0
    for graph in graphs:
        for block in graph.iterblocks():
            if not block.operations:
                continue
            newoplist = []
            for i, op in enumerate(block.operations):
                if (op.opname == 'jit_force_virtualizable' and
                    match_virtualizable_type(op.args[0].concretetype,
                                             VTYPEPTR)):
                    if op.args[-1].value.get('access_directly', False):
                        continue
                    op.opname = 'direct_call'
                    op.args = [c_funcptr, op.args[0]]
                    count += 1
                newoplist.append(op)
            block.operations = newoplist
    log("replaced %d 'jit_force_virtualizable' with %r" % (count, funcptr))

def match_virtualizable_type(TYPE, VTYPEPTR):
    if isinstance(TYPE, ootype.Instance):
        # ootype only: any subtype may be used
        return ootype.isSubclass(TYPE, VTYPEPTR)
    else:
        # lltype, or ootype with a TYPE that is e.g. an ootype.Record
        return TYPE == VTYPEPTR
