from pypy.interpreter.typedef import GetSetProperty
from pypy.module.exceptions.interp_exceptions import W_BaseException
from pypy.objspace.fake.checkmodule import checkmodule

def test_checkmodule():
    # XXX: PyTraceback usage in these methods blows up checkmodule
    def descr_gettraceback(self, space):
        return space.w_None
    def descr_settraceback(self, space, w_newtraceback):
        pass
    W_BaseException.descr_gettraceback = descr_gettraceback
    W_BaseException.descr_settraceback = descr_settraceback
    W_BaseException.typedef.add_entries(
        __traceback__=GetSetProperty(descr_gettraceback, descr_settraceback))
    checkmodule('_io')
