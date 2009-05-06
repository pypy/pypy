from pypy.rpython.rmodel import inputconst
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import InstanceRepr, mangle
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class VirtualizableAccessor(AbstractVirtualizableAccessor):

    def initialize(self, TYPE, redirected_fields, PARENT=None):
        pass # TODO

    def prepare_getsets(self):
        self.getsets = {} # TODO


class Virtualizable2InstanceRepr(AbstractVirtualizable2InstanceRepr, InstanceRepr):

    VirtualizableAccessor = VirtualizableAccessor
    op_getfield = 'oogetfield'
    op_setfield = 'oosetfield'

    def _setup_instance_repr(self):
        InstanceRepr._setup_repr(self, hints = {'virtualizable2': True,
                                                'virtuals' : self.virtuals})

    def gencast(self, llops, vinst):
        raise NotImplementedError

    def get_mangled_fields(self):
        return self.allfields.keys()

    def get_field(self, attr):
        mangled = mangle(attr, self.rtyper.getconfig())
        return mangled, self.allfields[mangled]

    def is_in_fields(self, attr):
        mangled = mangle(attr, self.rtyper.getconfig())
        return mangled in self.allfields

    def set_vable(self, llops, vinst, force_cast=False):
        pass # TODO
