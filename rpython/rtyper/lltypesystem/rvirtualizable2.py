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
