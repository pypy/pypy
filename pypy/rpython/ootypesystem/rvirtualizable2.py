from pypy.rpython.rmodel import inputconst
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import InstanceRepr, mangle, OBJECT
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr

VABLERTI = OBJECT


class VirtualizableAccessor(AbstractVirtualizableAccessor):
    pass


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    VirtualizableAccessor = VirtualizableAccessor

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_rti', VABLERTI))
        return llfields

    def get_field(self, attr):
        mangled = mangle(attr, self.rtyper.getconfig())
        return mangled, self.allfields[mangled]

    def set_vable(self, llops, vinst, force_cast=False):
        pass # TODO
