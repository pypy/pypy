from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import InstanceRepr, OBJECTPTR
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_token', lltype.Signed))
        return llfields

    def set_vable(self, llops, vinst, force_cast=False):
        if self.top_of_virtualizable_hierarchy:
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = inputconst(lltype.Void, 'vable_token')
            cvalue = inputconst(lltype.Signed, 0)
            llops.genop('setfield', [vinst, cname, cvalue])
        else:
            self.rbase.set_vable(llops, vinst, force_cast=True)
