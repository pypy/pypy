
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel

def builder(initial_space=20):
    return []

class SomeStringBuilder(annmodel.SomeObject):
    def __init__(self, initial_space=0):
        self.initial_space = initial_space

    def method_append(self, s_item):
        if not isinstance(s_item, annmodel.SomeString):
            raise TypeError("Can only append strings or characters to string builder")
        return annmodel.SomeImpossibleValue()

    def method_build(self):
        return annmodel.SomeString()

class StringBuilderEntry(ExtRegistryEntry):
    _about_ = builder

    def compute_result_annotation(self, s_initial_space=None):
        if s_initial_space is None:
            initial_space = 0
        else:
            assert s_initial_space.is_constant()
            initial_space = s_initial_space.const
            assert isinstance(initial_space, int)
        return SomeStringBuilder(initial_space)
