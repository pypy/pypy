from pypy.rpython.rmodel import inputconst
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rclass import InstanceRepr
from pypy.rpython.rvirtualizable2 import AbstractVirtualizableAccessor
from pypy.rpython.rvirtualizable2 import AbstractVirtualizable2InstanceRepr


class VirtualizableAccessor(AbstractVirtualizableAccessor):

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
        #return llops.genop('cast_pointer', [vinst], resulttype=self)

    def set_vable(self, llops, vinst, force_cast=False):
        pass # TODO
