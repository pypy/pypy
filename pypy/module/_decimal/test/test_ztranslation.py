
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.module._decimal import Module

def test_checkmodule():
    Module.interpleveldefs['__hack'] = (
        'interp_decimal.unicodeobject.W_UnicodeObject(u"")')
    checkmodule('_decimal')

