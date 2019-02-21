from pypy.objspace.fake.checkmodule import checkmodule
import py, sys

if sys.platform == 'win32':
    py.test.skip("not used on win32") 

def test_posixsubprocess_translates():
    checkmodule('_posixsubprocess')
