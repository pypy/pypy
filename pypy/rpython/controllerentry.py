from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.extregistry import ExtRegistryEntry


class SomeControlledInstance(annmodel.SomeObject):

    def __init__(self, classdef, originaltype):
        self.classdef = classdef
        self.knowntype = originaltype

    def s_implself(self):
        return annmodel.SomeInstance(self.classdef)

    def delegate(self, methodname, *args_s):
        bk = getbookkeeper()
        classdef = self.classdef
        # emulate a getattr to make sure it's on the classdef
        classdef.find_attribute(methodname)
        origindesc = classdef.classdesc.lookup(methodname)
        s_func = origindesc.s_read_attribute(methodname)
        funcdesc, = s_func.descriptions
        methdesc = bk.getmethoddesc(
            funcdesc,
            origindesc.getuniqueclassdef(),
            classdef,
            methodname)
        s_meth = annmodel.SomePBC([methdesc])
        return bk.emulate_pbc_call(bk.position_key, s_meth, args_s,
                                   callback = bk.position_key)


class __extend__(SomeControlledInstance):

    def getattr(s_cin, s_attr):
        assert s_attr.is_constant()
        assert isinstance(s_attr.const, str)
        return s_cin.delegate('get_' + s_attr.const)


class ControllerEntry(ExtRegistryEntry):

    def compute_result_annotation(self):
        cls = self.instance
        classdef = self.bookkeeper.getuniqueclassdef(self._implementation_)
        return SomeControlledInstance(classdef, cls)
