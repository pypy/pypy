from pypy.annotation.model import SomeInteger, SomePBC
from pypy.objspace.flow.model import SpaceOperation
from pypy.interpreter.miscutils import getthreadlocals


class CType(object):

    def __init__(self, translator):
        self.translator = translator

    def convert_to_obj(self, typer, v1, v2):
        return [SpaceOperation("conv_to_obj", [v1], v2)]

    def convert_from_obj(self, typer, v1, v2):
        return [SpaceOperation("conv_from_obj", [v1], v2)]

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

    def nameof(self, v, debug=None):
        return '%d' % (v,)

    def fn_conv_to_obj(self):
        return 'PyInt_FromLong'

    def fn_conv_from_obj(self):
        return 'PyInt_AsLong'


class CNoneType(CType):
    error_return  = '-1'
    ctypetemplate = 'int %s'
    s_annotation  = SomePBC({None: True})

    def nameof(self, v, debug=None):
        assert v is None
        return '0'

    def fn_conv_to_obj(self):
        return 'PyNone_FromInt'

    def fn_conv_from_obj(self):
        return 'PyNone_AsInt'
