from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype

class Entry_oostring(ExtRegistryEntry):
    _about_ = ootype.oostring

    def compute_result_annotation(self, obj_s, base_s):
        assert isinstance(obj_s, (annmodel.SomeInteger,
                                  annmodel.SomeChar,
                                  annmodel.SomeFloat,
                                  annmodel.SomeOOInstance,
                                  annmodel.SomeString))
        assert isinstance(base_s, annmodel.SomeInteger)
        return annmodel.SomeOOInstance(ootype.String)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0],(annmodel.SomeInteger,
                                         annmodel.SomeChar,
                                         annmodel.SomeString,
                                         annmodel.SomeFloat,
                                         annmodel.SomeOOInstance,
                                         annmodel.SomeString))
        vlist = hop.inputargs(hop.args_r[0], ootype.Signed)
        return hop.genop('oostring', vlist, resulttype = ootype.String)

class Entry_oounicode(ExtRegistryEntry):
    _about_ = ootype.oounicode

    def compute_result_annotation(self, obj_s, base_s):
        assert isinstance(obj_s, annmodel.SomeUnicodeCodePoint) or \
               (isinstance(obj_s, annmodel.SomeOOInstance)
                and obj_s.ootype in (ootype.String, ootype.Unicode))
        assert isinstance(base_s, annmodel.SomeInteger)
        return annmodel.SomeOOInstance(ootype.Unicode)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], (annmodel.SomeUnicodeCodePoint,
                                          annmodel.SomeOOInstance))
        vlist = hop.inputargs(hop.args_r[0], ootype.Signed)
        return hop.genop('oounicode', vlist, resulttype = ootype.Unicode)
    

class Entry_ootype_string(ExtRegistryEntry):
    _type_ = ootype._string

    def compute_annotation(self):
        return annmodel.SomeOOInstance(ootype=ootype.String)


class Entry_ooparse_int(ExtRegistryEntry):
    _about_ = ootype.ooparse_int

    def compute_result_annotation(self, str_s, base_s):
        assert isinstance(str_s, annmodel.SomeOOInstance)\
               and str_s.ootype is ootype.String
        assert isinstance(base_s, annmodel.SomeInteger)
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)\
               and hop.args_s[0].ootype is ootype.String
        vlist = hop.inputargs(hop.args_r[0], ootype.Signed)
        hop.has_implicit_exception(ValueError)
        hop.exception_is_here()
        return hop.genop('ooparse_int', vlist, resulttype = ootype.Signed)


class Entry_ooparse_float(ExtRegistryEntry):
    _about_ = ootype.ooparse_float

    def compute_result_annotation(self, str_s):
        assert isinstance(str_s, annmodel.SomeOOInstance)\
               and str_s.ootype is ootype.String
        return annmodel.SomeFloat()

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)\
               and hop.args_s[0].ootype is ootype.String
        vlist = hop.inputargs(hop.args_r[0])
        hop.has_implicit_exception(ValueError)
        hop.exception_is_here()
        return hop.genop('ooparse_float', vlist, resulttype = ootype.Float)
