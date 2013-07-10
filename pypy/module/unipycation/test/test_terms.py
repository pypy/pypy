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

        # make a load of variables
        vs = [ upy.Var() for x in range(10) ]

        # no two distinct vars should have the same name
        combos = [ (x, y) for x in vs for y in vs if x != y ]
        same_name = [ (x, y) for (x, y) in combos if x.name == y.name ]

        assert same_name == []
