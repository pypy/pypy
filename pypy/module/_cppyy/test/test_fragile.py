import py, os, sys

currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("fragileDict.so"))


def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make fragileDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestFRAGILE:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_fragile = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_load_failure(self):
        """Test failure to load dictionary"""

        import _cppyy
        raises(RuntimeError, _cppyy.load_reflection_info, "does_not_exist.so")

        try:
            _cppyy.load_reflection_info("does_not_exist.so")
        except RuntimeError as e:
            assert "does_not_exist.so" in str(e)

    def test02_missing_classes(self):
        """Test (non-)access to missing classes"""

        import _cppyy

        raises(AttributeError, getattr, _cppyy.gbl, "no_such_class")

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        raises(AttributeError, getattr, fragile, "no_such_class")

        assert fragile.C == fragile.C
        assert fragile.C().check() == ord('C')

        assert fragile.B == fragile.B
        assert fragile.B().check() == ord('B')
        raises(AttributeError, getattr, fragile.B().gime_no_such(), "_cpp_proxy")

        assert fragile.C == fragile.C
        assert fragile.C().check() == ord('C')
        raises(TypeError, fragile.C().use_no_such, None)

    def test03_arguments(self):
        """Test reporting when providing wrong arguments"""

        import _cppyy

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        assert fragile.D == fragile.D
        assert fragile.D().check() == ord('D')

        d = fragile.D()
        raises(TypeError, d.overload, None)
        raises(TypeError, d.overload, None, None, None)

        d.overload('a')
        d.overload(1)

    def test04_unsupported_arguments(self):
        """Test arguments that are yet unsupported"""

        import _cppyy

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        assert fragile.E == fragile.E
        assert fragile.E().check() == ord('E')

        e = fragile.E()
        raises(TypeError, e.overload, None)
        raises(TypeError, getattr, e, 'm_pp_no_such')

    def test05_wrong_arg_addressof(self):
        """Test addressof() error reporting"""

        import _cppyy

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        assert fragile.F == fragile.F
        assert fragile.F().check() == ord('F')

        f = fragile.F()
        o = object()

        _cppyy.addressof(f)
        raises(TypeError, _cppyy.addressof, o)
        raises(TypeError, _cppyy.addressof, 1)
        # 0, None, and nullptr allowed
        assert _cppyy.addressof(0)                  == 0
        assert _cppyy.addressof(None)               == 0
        assert _cppyy.addressof(_cppyy.gbl.nullptr) == 0

    def test06_wrong_this(self):
        """Test that using an incorrect self argument raises"""

        import _cppyy

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        a = fragile.A()
        assert fragile.A.check(a) == ord('A')

        b = fragile.B()
        assert fragile.B.check(b) == ord('B')
        raises(TypeError, fragile.A.check, b)
        raises(TypeError, fragile.B.check, a)

        assert not a.gime_null()

        assert isinstance(a.gime_null(), fragile.A)
        raises(ReferenceError, fragile.A.check, a.gime_null())

    def test07_unnamed_enum(self):
        """Test that an unnamed enum does not cause infinite recursion"""

        import _cppyy

        assert _cppyy.gbl.fragile is _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile
        assert _cppyy.gbl.fragile is fragile

        g = fragile.G()

    def test08_unhandled_scoped_datamember(self):
        """Test that an unhandled scoped data member does not cause infinite recursion"""

        import _cppyy

        assert _cppyy.gbl.fragile is _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile
        assert _cppyy.gbl.fragile is fragile

        h = fragile.H()

    def test09_operator_bool(self):
        """Access to global vars with an operator bool() returning False"""

        import _cppyy

        i = _cppyy.gbl.fragile.I()
        assert not i

        g = _cppyy.gbl.fragile.gI
        assert not g

    def test10_documentation(self):
        """Check contents of documentation"""

        import _cppyy

        assert _cppyy.gbl.fragile == _cppyy.gbl.fragile
        fragile = _cppyy.gbl.fragile

        d = fragile.D()
        try:
            d.check(None)         # raises TypeError
            assert 0
        except TypeError as e:
            assert "fragile::D::check()" in str(e)
            assert "TypeError: wrong number of arguments" in str(e)

        try:
            d.overload(None)      # raises TypeError
            assert 0
        except TypeError as e:
            assert "fragile::D::overload()" in str(e)
            assert "TypeError: wrong number of arguments" in str(e)
            assert "fragile::D::overload(fragile::no_such_class*)" in str(e)
            assert "TypeError: no converter available for 'fragile::no_such_class*'" in str(e)
            assert "fragile::D::overload(char, int)" in str(e)
            assert "TypeError: expected string, got NoneType object" in str(e)
            assert "fragile::D::overload(int, fragile::no_such_class*)" in str(e)
            assert "TypeError: expected integer, got NoneType object" in str(e)

        j = fragile.J()
        assert fragile.J.method1.__doc__ == j.method1.__doc__
        assert j.method1.__doc__ == "int fragile::J::method1(int, double)"

        f = fragile.fglobal
        assert f.__doc__ == "void fragile::fglobal(int, double, char)"

        try:
            o = fragile.O()       # raises TypeError
            assert 0
        except TypeError as e:
            assert "cannot instantiate abstract class 'O'" in str(e)

    def test11_dir(self):
        """Test __dir__ method"""

        import _cppyy

        members = dir(_cppyy.gbl.fragile)
        assert 'A' in members
        assert 'B' in members
        assert 'C' in members
        assert 'D' in members                 # classes

        assert 'nested1' in members           # namespace

        # TODO: think this through ... probably want this, but interferes with
        # the (new) policy of lazy lookups
        #assert 'fglobal' in members          # function
        #assert 'gI'in members                # variable

    def test12_imports(self):
        """Test ability to import from namespace (or fail with ImportError)"""

        import _cppyy

        # TODO: namespaces aren't loaded (and thus not added to sys.modules)
        # with just the from ... import statement; actual use is needed
        from _cppyy.gbl import fragile

        def fail_import():
            from _cppyy.gbl import does_not_exist
        raises(ImportError, fail_import)

        from _cppyy.gbl.fragile import A, B, C, D
        assert _cppyy.gbl.fragile.A is A
        assert _cppyy.gbl.fragile.B is B
        assert _cppyy.gbl.fragile.C is C
        assert _cppyy.gbl.fragile.D is D

        # according to warnings, can't test "import *" ...

        from _cppyy.gbl.fragile import nested1
        assert _cppyy.gbl.fragile.nested1 is nested1

        from _cppyy.gbl.fragile.nested1 import A, nested2
        assert _cppyy.gbl.fragile.nested1.A is A
        assert _cppyy.gbl.fragile.nested1.nested2 is nested2

        from _cppyy.gbl.fragile.nested1.nested2 import A, nested3
        assert _cppyy.gbl.fragile.nested1.nested2.A is A
        assert _cppyy.gbl.fragile.nested1.nested2.nested3 is nested3

        from _cppyy.gbl.fragile.nested1.nested2.nested3 import A
        assert _cppyy.gbl.fragile.nested1.nested2.nested3.A is nested3.A

    def test13_missing_casts(self):
        """Test proper handling when a hierarchy is not fully available"""

        import _cppyy

        k = _cppyy.gbl.fragile.K()

        assert k is k.GimeK(False)
        assert k is not k.GimeK(True)

        kd = k.GimeK(True)
        assert kd is k.GimeK(True)
        assert kd is not k.GimeK(False)

        l = k.GimeL()
        assert l is k.GimeL()

    def test14_double_enum_trouble(self):
        """Test a redefinition of enum in a derived class"""

        return # don't bother; is fixed in cling-support

        import _cppyy

        M = _cppyy.gbl.fragile.M
        N = _cppyy.gbl.fragile.N

        assert M.kOnce == N.kOnce
        assert M.kTwice == N.kTwice
        assert M.__dict__['kTwice'] is not N.__dict__['kTwice']
