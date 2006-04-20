import py
from pypy.translator.llvm.wrapable.llvm import *


#XXX The tests below were shamefully never written when writing the rest of the code and
#    should therefor be filled in by Eric asap.

def test_misc():
    print 'Module("mine")'
    mod = Module('mine')
    print 'mod=', mod
    print 'mod.instance=', mod.instance
    print
    assert mod.n_functions() == 0

    print 'ExistingModuleProvider(mod)'
    mp = ExistingModuleProvider(mod)
    print 'mp=', mp
    print 'mp.instance=', mp.instance
    print

    ee = ExecutionEngine(mp)
    #ee = ExecutionEngine.create(mp)    #same
    print 'ee=', ee
    #print 'ee.instance=', ee.instance  #can't do here because ee.create is staticmethod
    mod2 = ee.getModule()
    print mod2

    print 'mod.getModuleIdentifier()'
    modId = mod.getModuleIdentifier()
    print 'modId=', modId
    assert modId == 'mine'
    assert modId == mod2.getModuleIdentifier()

def test_wrapable_create():
    pass

def test_global_function():
    pass

def test_class():
    pass

def test_class_ctor():
    pass

def test_class_dtor():
    pass

def test_method():
    pass

def test_staticmethod():
    pass

def test_staticmethod_as_factory(): #self.instance can not be set in this case
    pass

def test_classmethod():
    pass

def test_include():
    pass

def test_include_py():
    pass

def test_call_pymethod():
    pass

def test_call_pyctor():
    pass

def test_call_pystaticmethod():
    pass

def test_call_pyclassmethod():
    pass

def test_call_pyfunction():
    pass

def test_cpp_cast():
    pass

def test_py_cast():
    pass

def test_enum():
    pass

def test_structure():
    pass

def test_ref_ptr_inst():
    pass

def test_default_arguments():
    pass
