from rpython.rtyper.rmodel import inputconst
from rpython.rtyper.ootypesystem import ootype
from rpython.rtyper.ootypesystem.rclass import InstanceRepr, mangle, OBJECT
from rpython.rtyper.rvirtualizable2 import AbstractVirtualizable2InstanceRepr

VABLERTI = OBJECT


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_token', VABLERTI))
        return llfields

    def set_vable(self, llops, vinst, force_cast=False):
        pass # TODO
