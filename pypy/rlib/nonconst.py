
""" simple non-constant constant. Ie constant which does not get annotated as constant
"""

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.objspace.flow.model import Constant

class NonConstant(object):
    def __init__(self, _constant):
        self.__dict__['constant'] = _constant

    def __getattr__(self, attr):
        return getattr(self.__dict__['constant'], attr)

    def __setattr__(self, attr, value):
        setattr(self.__dict__['constant'], attr, value)

    def __nonzero__(self):
        return bool(self.__dict__['constant'])

    def __eq__(self, other):
        return self.__dict__['constant'] == other

    def __add__(self, other):
        return self.__dict__['constant'] + other

class EntryNonConstant(ExtRegistryEntry):
    _about_ = NonConstant

    def compute_result_annotation(self, arg):
        if hasattr(arg, 'const'):
            return self.bookkeeper.immutablevalue(arg.const, False)
        else:
            return arg

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        retval = Constant(hop.r_result.convert_const(hop.args_v[0].value))
        retval.concretetype = hop.r_result.lowleveltype
        return retval

