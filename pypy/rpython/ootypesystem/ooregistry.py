from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype

class OOStringEntry(ExtRegistryEntry):
    _about_ = ootype.oostring2

    def compute_result_annotation(self, obj_s, base_s):
        assert isinstance(obj_s, (annmodel.SomeInteger,
                                annmodel.SomeChar,
                                annmodel.SomeOOInstance))
        assert isinstance(base_s, annmodel.SomeInteger)
        return annmodel.SomeOOInstance(ootype.String)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0],(annmodel.SomeInteger,
                                         annmodel.SomeChar,
                                         annmodel.SomeString,
                                         annmodel.SomeOOInstance))
        assert isinstance(hop.args_s[1], annmodel.SomeInteger)
        return hop.genop('oostring', hop.args_v, resulttype = ootype.String)
        
