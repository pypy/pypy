from pypy.annotation.model import SomeInteger, SomePBC
from pypy.objspace.flow.model import SpaceOperation
from pypy.interpreter.miscutils import getthreadlocals


class CType(object):

    def __init__(self, translator):
        self.translator = translator

    def convert_to_obj(self, typer, v1, v2):
        return [SpaceOperation(self.opname_conv_to_obj, [v1], v2)]

    def convert_from_obj(self, typer, v1, v2):
        return [SpaceOperation(self.opname_conv_from_obj, [v1], v2)]

    def debugname(self):
        return self.__class__.__name__

    def genc():
        """A hack to get at the currently running GenC instance."""
        return getthreadlocals().genc
    genc = staticmethod(genc)

    def init_globals(self, genc):
        return []

    def collect_globals(self, genc):
        return []

    def cincref(self, expr):
        return ''

    def cdecref(self, expr):
        return ''


class CIntType(CType):
    error_return  = '-1'
    ctypetemplate = 'int %s'
    s_annotation  = SomeInteger()
    opname_conv_to_obj   = 'int2obj'
    opname_conv_from_obj = 'obj2int'

    def nameof(self, v, debug=None):
        return '%d' % (v,)


class CNoneType(CType):
    error_return  = '-1'
    ctypetemplate = 'int %s'
    s_annotation  = SomePBC({None: True})
    opname_conv_to_obj   = 'none2obj'
    opname_conv_from_obj = 'obj2none'

    def nameof(self, v, debug=None):
        assert v is None
        return '0'
