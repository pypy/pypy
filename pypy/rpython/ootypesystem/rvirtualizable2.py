from pypy.rpython.rmodel import inputconst
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import InstanceRepr, mangle
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class VirtualizableAccessor(AbstractVirtualizableAccessor):
    pass


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    VirtualizableAccessor = VirtualizableAccessor

    def _setup_repr_llfields(self):
        return None      # TODO

    def get_field(self, attr):
        mangled = mangle(attr, self.rtyper.getconfig())
        return mangled, self.allfields[mangled]

    def set_vable(self, llops, vinst, force_cast=False):
        pass # TODO
