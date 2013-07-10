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

        vs = [ upy.Var() for x in range(10) ]

        # Each var should have a distinct internal pyrolog BindingVar
        # This is exposed in str() of a Var.
        # No two Var's should have the same str()
        str_combos = [ (str(x), str(y)) for x in vs for y in vs if x != y ]
        print(str_combos)
        same_str = [ (x, y) for (x, y) in str_combos if x == y ]

        assert same_str == []
