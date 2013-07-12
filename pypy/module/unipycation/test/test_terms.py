#import pypy.module.unipycation.conversion as conv
#import pypy.module.unipycation.util as util
#import pypy.module.unipycation.objects as objects
#from pypy.interpreter.error import OperationError
#import prolog.interpreter.signature as psig

#import prolog.interpreter.term as pterm
#import pypy.module.unipycation.app_error as err
import pytest

class AppTestTerms(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_var(self):
        import unipycation as upy
        N = 10

        vs = [ upy.Var() for x in range(N) ]

        for i in range(N):
            assert str(vs[i]) == ("V%d" % i)
