from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rvirtualizable import VABLERTIPTR
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class VirtualizableAccessor(AbstractVirtualizableAccessor):
    pass


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
