
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.interpreter.mixedmodule import getinterpevalloader
from pypy.module._decimal import Module

def test_checkmodule():
    Module.buildloaders()
    Module.loaders['__hack'] = getinterpevalloader(
        'pypy.objspace.std', 'unicodeobject.W_UnicodeObject(u"")')
    checkmodule('_decimal')

