from __future__ import generators
from py import test, path
from py.magic import autopath ; autopath = autopath()
from py.__impl__.test import collect 

testdir = autopath.dirpath('test') 
assert testdir.check(dir=1)
datadir = testdir / 'data'


def test_failing_import_execfile():
    fn = datadir / 'failingimport.py' 
    l = list(collect.Module(path.extpy(fn)))
    assert l
    ex, = l
    assert issubclass(ex.excinfo[0], ImportError)
       
def test_failing_import_directory():
    class MyDirectory(collect.Directory):
        fil = path.checker(basestarts="testspecial_", ext='.py')
    l = list(MyDirectory(datadir))
    assert len(l) == 1
    assert isinstance(l[0], collect.Module)
    l2 = list(l[0])
    assert l2
    exc = l2[0]
    assert isinstance(exc, collect.Error)
    assert issubclass(exc.excinfo[0], ImportError)

def test_module_file_not_found():
    fn = testdir.join('nada','no')
    l = list(collect.Module(fn))
    assert len(l) == 1
    assert isinstance(l[0], collect.Error)
    assert isinstance(l[0].excinfo[1], path.NotFound) 

def test_syntax_error_in_module():
    modpath = 'py.__impl__.test.data.syntax_error.whatever'
    l2 = list(collect.Module(modpath))
    assert len(l2) == 1
    assert isinstance(l2[0], collect.Error)
    assert issubclass(l2[0].excinfo[0], path.Invalid)

def test_disabled_class():
    extpy = path.extpy(datadir.join('disabled.py'))
    l = list(collect.Class(extpy))
    assert len(l) == 0

class TestCustomCollector:
    def test_custom_collect(self):
        l = list(collect.Module(datadir.join('Collector.py')))
        assert len(l) == 3
        for item in l:
            assert isinstance(item, test.Item) 
        #for x in l2:
        #    assert isinstance(x, Unit) 
        #    x.execute() 
        
class Testsomeclass:
    disabled = True
    def test_something():
        raise ValueError

l = []
def test_1():
    l.append(1)
def test_2():
    l.append(2)
def test_3():
    assert l == [1,2]
class Testmygroup:
    reslist = []
    def test_1(self):
        self.reslist.append(1)
    def test_2(self):
        self.reslist.append(2)
    def test_3(self):
        self.reslist.append(3)
    def test_4(self):
        assert self.reslist == [1,2,3]
