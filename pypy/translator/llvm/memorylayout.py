import autopath
import sets

from types import FunctionType

from pypy.translator.llvm.representation import debug, LLVMRepr
from pypy.translator.llvm.typerepr import TypeRepr, PointerTypeRepr

debug = True

class MemoryLayout(object):
    def __init__(self, attrs, l_types, gen):
        self.attrs = attrs
        self.l_types = l_types
        self.attr_num = dict(zip(attrs, range(len(attrs))))
        self.gen = gen

    def extend_layout(self, attrs, l_types):
        return MemoryLayout(self.attrs + attrs, self.l_types + l_types,
                            self.gen)

    def layouts_match(self, other, attrs): #XXX
        for attr in attrs:
            if self.attr_num[attr] != other.attr_num[attr]:
                return False
            if (self.l_types[self.attr_num[attr]].typename() !=
                other.l_types[other.attr_num[attr]].typename()):
                return False
        return True

    def merge_layouts(self, other, attrs): #XXX
        attrs = []
        l_types = []
        for i, attr in enumerate(self.attrs):
            l_types.append(self.l_types[i])
            if attr in attrs:
                attrs.append(attr)
            else:
                l_types.append(self.attrs[i])

    def get(self, l_target,  l_object, attr, lblock, l_func):
        assert attr in self.attr_num
        if debug:
            print self.attrs
            print attr
        l_pter = self.gen.get_local_tmp(
            PointerTypeRepr(l_target.llvmtype(), self.gen), l_func)
        lblock.getelementptr(l_pter, l_object,
                             [0, self.attr_num[attr]])
        lblock.load(l_target, l_pter)

    def set(self, l_object, attr, l_value, lblock, l_func):
        assert attr in self.attr_num
        l_type = self.l_types[self.attr_num[attr]]
        if l_value.llvmtype() != l_type.typename():
            l_cast = self.gen.get_local_tmp(l_type, l_func)
            l_func.dependencies.add(l_cast)
            lblock.cast(l_cast, l_value)
            l_value = l_cast
        l_pter = self.gen.get_local_tmp(
            PointerTypeRepr(l_value.llvmtype(), self.gen), l_func)
        lblock.getelementptr(l_pter, l_object, [0, self.attr_num[attr]])
        lblock.store(l_value, l_pter)

    def definition(self):
        attributes = ", ".join([at.typename() for at in self.l_types])
        return "type {%s}" % attributes

    def constant(self, l_values):
        assert len(l_values) == len(self.attrs)
        attrs = ", ".join([at.typename() + " " + av.llvmname()
                           for at, av in zip(self.l_types, l_values)])
        return "{%s}" % attrs

        
