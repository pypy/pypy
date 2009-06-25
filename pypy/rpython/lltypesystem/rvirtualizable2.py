from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rvirtualizable import VABLERTIPTR
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class VirtualizableAccessor(AbstractVirtualizableAccessor):

    def prepare_getsets(self):
        self.getsets = {}
        STRUCT = self.TYPE
        for fieldname in self.redirected_fields:
            FIELDTYPE = getattr(STRUCT, fieldname)
            GETTER = lltype.FuncType([lltype.Ptr(STRUCT)], FIELDTYPE)
            SETTER = lltype.FuncType([lltype.Ptr(STRUCT), FIELDTYPE],
                                     lltype.Void)
            VABLE_GETSET = lltype.Struct('vable_getset',
                                         ('get', lltype.Ptr(GETTER)),
                                         ('set', lltype.Ptr(SETTER)),
                                         hints={'immutable': True})
            getset = lltype.malloc(VABLE_GETSET, flavor='raw', zero=False)
            # as long as no valid pointer has been put in the structure
            # by the JIT, accessing the fields should raise, in order
            # to prevent constant-folding
            import py
            py.test.raises(lltype.UninitializedMemoryAccess, "getset.get")
            py.test.raises(lltype.UninitializedMemoryAccess, "getset.set")
            self.getsets[fieldname] = getset
            setattr(self, 'getset_' + fieldname, getset)


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    VirtualizableAccessor = VirtualizableAccessor

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_base', llmemory.Address))
            llfields.append(('vable_rti', VABLERTIPTR))
        return llfields

    def get_field(self, attr):
        return self.fields[attr]

    def set_vable(self, llops, vinst, force_cast=False):
        if self.top_of_virtualizable_hierarchy:
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = inputconst(lltype.Void, 'vable_rti')
            vvalue = inputconst(VABLERTIPTR, lltype.nullptr(VABLERTIPTR.TO))
            llops.genop('setfield', [vinst, cname, vvalue])
        else:
            self.rbase.set_vable(llops, vinst, force_cast=True)
