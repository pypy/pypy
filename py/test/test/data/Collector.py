from __future__ import generators
from py.test import collect

class Collector(collect.PyCollector):
    def collect_function(self, pypath):
        if pypath.check(func=1, basestarts='myprefix_'):
            yield self.Item(pypath, pypath.basename) 

def myprefix_1(arg):
    assert arg == 'myprefix_1'
def myprefix_2(arg):
    assert arg == 'myprefix_2'
def myprefix_3(arg):
    assert arg == 'myprefix_3'

def test_this_should_not_be_called():
    assert 1 != 0, "should not be collected" 

class A:
    def test_this_should_not_be_called(self):
        assert 1 != 0, "should not be collected" 
