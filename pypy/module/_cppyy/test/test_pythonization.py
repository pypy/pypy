import py, os, sys
from pytest import raises
from .support import setup_make


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("pythonizablesDict.so"))

def setup_module(mod):
    setup_make("pythonizablesDict.so")

class AppTestPYTHONIZATION:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_datatypes = cls.space.appexec([], """():
            import ctypes, _cppyy
            _cppyy._post_import_startup()
            return ctypes.CDLL(%r, ctypes.RTLD_GLOBAL)""" % (test_dct, ))

    def test00_api(self):
        """Test basic semantics of the pythonization API"""

        import _cppyy

        raises(TypeError, _cppyy.add_pythonization, 1)

        def pythonizor1(klass, name):
            pass

        def pythonizor2(klass, name):
            pass

        pythonizor3 = pythonizor1

        _cppyy.add_pythonization(pythonizor1)
        assert _cppyy.remove_pythonization(pythonizor2) == False
        assert _cppyy.remove_pythonization(pythonizor3) == True

    def test01_more_api(self):
        """Further API semantics"""

        import _cppyy as cppyy

        def pythonizor(klass, name):
            if name == 'pyzables::SomeDummy1':
                klass.test = 1

        cppyy.add_pythonization(pythonizor)
        assert cppyy.gbl.pyzables.SomeDummy1.test == 1

        def pythonizor(klass, name):
            if name == 'SomeDummy2':
                klass.test = 2
        cppyy.add_pythonization(pythonizor, 'pyzables')

        def pythonizor(klass, name):
            if name == 'pyzables::SomeDummy2':
                klass.test = 3
        cppyy.add_pythonization(pythonizor)

        assert cppyy.gbl.pyzables.SomeDummy2.test == 2

        def root_pythonizor(klass, name):
            if name == 'TString':
                klass.__len__ = klass.Length

        cppyy.add_pythonization(root_pythonizor)

        assert len(cppyy.gbl.TString("aap")) == 3

    def test02_type_pinning(self):
        """Verify pinnability of returns"""

        import _cppyy as cppyy

        cppyy.gbl.pyzables.GimeDerived._creates = True

        result = cppyy.gbl.pyzables.GimeDerived()
        assert type(result) == cppyy.gbl.pyzables.MyDerived

        cppyy._pin_type(cppyy.gbl.pyzables.MyBase)
        assert type(result) == cppyy.gbl.pyzables.MyDerived


    def test03_transparency(self):
        """Transparent use of smart pointers"""

        import _cppyy as cppyy

        Countable = cppyy.gbl.pyzables.Countable
        mine = cppyy.gbl.pyzables.mine

        assert type(mine) == Countable
        assert mine.m_check == 0xcdcdcdcd
        assert type(mine.__smartptr__()) == cppyy.gbl.std.shared_ptr(Countable)
        assert mine.__smartptr__().get().m_check == 0xcdcdcdcd
        assert mine.say_hi() == "Hi!"

    def test04_converters(self):
        """Smart pointer argument passing"""

        import _cppyy as cppyy

        pz = cppyy.gbl.pyzables
        mine = pz.mine

        assert 0xcdcdcdcd == pz.pass_mine_rp_ptr(mine)
        assert 0xcdcdcdcd == pz.pass_mine_rp_ref(mine)
        assert 0xcdcdcdcd == pz.pass_mine_rp(mine)

        assert 0xcdcdcdcd == pz.pass_mine_sp_ptr(mine)
        assert 0xcdcdcdcd == pz.pass_mine_sp_ref(mine)

        assert 0xcdcdcdcd == pz.pass_mine_sp_ptr(mine.__smartptr__())
        assert 0xcdcdcdcd == pz.pass_mine_sp_ref(mine.__smartptr__())

        assert 0xcdcdcdcd == pz.pass_mine_sp(mine)
        assert 0xcdcdcdcd == pz.pass_mine_sp(mine.__smartptr__())

        # TODO:
        # cppyy.gbl.mine = mine
        pz.renew_mine()

    def test05_executors(self):
        """Smart pointer return types"""

        import _cppyy as cppyy

        pz = cppyy.gbl.pyzables
        Countable = pz.Countable

        mine = pz.gime_mine_ptr()
        assert type(mine) == Countable
        assert type(mine.__smartptr__()) == cppyy.gbl.std.shared_ptr(Countable)
        assert mine.say_hi() == "Hi!"

        mine = pz.gime_mine_ref()
        assert type(mine) == Countable
        assert type(mine.__smartptr__()) == cppyy.gbl.std.shared_ptr(Countable)
        assert mine.say_hi() == "Hi!"

        mine = pz.gime_mine()
        assert type(mine) == Countable
        assert type(mine.__smartptr__()) == cppyy.gbl.std.shared_ptr(Countable)
        assert mine.say_hi() == "Hi!"
