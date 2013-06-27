from rpython.rtyper.lltypesystem import llmemory
from rpython.rtyper.lltypesystem.rclass import InstanceRepr
from rpython.rtyper.rvirtualizable import AbstractVirtualizableInstanceRepr


class VirtualizableInstanceRepr(AbstractVirtualizableInstanceRepr,
                                InstanceRepr):
    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_token', llmemory.GCREF))
        return llfields
