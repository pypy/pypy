from __future__ import generators
from py import test
from py.test import config 

class MyClass:
    def getoptions(self):
        yield config.Option('-v', action="count", dest="verbose", help="verbose")

def xtest_verbose():
    obj = MyClass()
    args = config.parseargs(['-v', 'hello'], obj)
    assert args == ['hello']
    assert hasattr(obj, 'option')
    assert hasattr(obj.option, 'verbose')
    assert obj.option.verbose

def xtest_verbose_default():
    obj = MyClass()
    args = config.parseargs(['hello'], obj)
    assert args, ['hello']
    assert hasattr(obj, 'option')
    assert hasattr(obj.option, 'verbose')
    assert not obj.option.verbose

def test_tmpdir():
    d1 = config.tmpdir 
    d2 = config.tmpdir 
    assert d1 == d2
        
test.main()
