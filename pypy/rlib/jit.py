from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import CDefinedIntSymbolic

def purefunction(func):
    func._pure_function_ = True
    return func

def hint(x, **kwds):
    return x

class Entry(ExtRegistryEntry):
    _about_ = hint

    def compute_result_annotation(self, s_x, **kwds_s):
        from pypy.annotation import model as annmodel
        s_x = annmodel.not_const(s_x)
        if 's_access_directly' in kwds_s:
            if isinstance(s_x, annmodel.SomeInstance):
                from pypy.objspace.flow.model import Constant
                classdesc = s_x.classdef.classdesc
                virtualizable = classdesc.read_attribute('_virtualizable_',
                                                         Constant(False)).value
                if virtualizable:
                    flags = s_x.flags.copy()
                    flags['access_directly'] = True
                    s_x = annmodel.SomeInstance(s_x.classdef,
                                                s_x.can_be_None,
                                                flags)
        return s_x

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        hints = {}
        for key, index in kwds_i.items():
            s_value = hop.args_s[index]
            if not s_value.is_constant():
                from pypy.rpython.error import TyperError
                raise TyperError("hint %r is not constant" % (key,))
            assert key.startswith('i_')
            hints[key[2:]] = s_value.const
        v = hop.inputarg(hop.args_r[0], arg=0)
        c_hint = hop.inputconst(lltype.Void, hints)
        hop.exception_cannot_occur()
        return hop.genop('hint', [v, c_hint], resulttype=v.concretetype)


def we_are_jitted():
    return False
# timeshifts to True

_we_are_jitted = CDefinedIntSymbolic('0 /* we are not jitted here */',
                                     default=0)

class Entry(ExtRegistryEntry):
    _about_ = we_are_jitted

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        return hop.inputconst(lltype.Signed, _we_are_jitted)

def _is_early_constant(x):
    return False

class Entry(ExtRegistryEntry):
    _about_ = _is_early_constant

    def compute_result_annotation(self, s_value):
        from pypy.annotation import model as annmodel
        s = annmodel.SomeBool()
        if s_value.is_constant():
            s.const = True
        return s

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        if hop.s_result.is_constant():
            assert hop.s_result.const
            return hop.inputconst(lltype.Bool, True)
        v, = hop.inputargs(hop.args_r[0])
        return hop.genop('is_early_constant', [v], resulttype=lltype.Bool)



