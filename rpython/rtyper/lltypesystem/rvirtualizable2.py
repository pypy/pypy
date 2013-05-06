from rpython.rtyper.rmodel import inputconst
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.rclass import InstanceRepr, OBJECTPTR
from rpython.rtyper.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_token', llmemory.GCREF))
        return llfields

##  The code below is commented out because vtable_token is always
##  initialized to NULL anyway.
##
##    def set_vable(self, llops, vinst, force_cast=False):
##        if self.top_of_virtualizable_hierarchy:
##            if force_cast:
##                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
##            cname = inputconst(lltype.Void, 'vable_token')
##            cvalue = inputconst(llmemory.GCREF,
##                                lltype.nullptr(llmemory.GCREF.TO))
##            llops.genop('setfield', [vinst, cname, cvalue])
##        else:
##            self.rbase.set_vable(llops, vinst, force_cast=True)
