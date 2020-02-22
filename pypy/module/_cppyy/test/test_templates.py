import py, os, sys
from .support import setup_make


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("templatesDict.so"))

def setup_module(mod):
    setup_make("templatesDict.so")

class AppTestTEMPLATES:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_templates = cls.space.appexec([], """():
            import ctypes, _cppyy
            _cppyy._post_import_startup()
            return ctypes.CDLL(%r, ctypes.RTLD_GLOBAL)""" % (test_dct, ))

    def test01_template_member_functions(self):
        """Template member functions lookup and calls"""

        import _cppyy

        m = _cppyy.gbl.MyTemplatedMethodClass()

      # implicit (called before other tests to check caching)
        assert m.get_size(1)          == m.get_int_size()+1
        assert 'get_size<int>' in dir(_cppyy.gbl.MyTemplatedMethodClass)

      # pre-instantiated
        assert m.get_size['char']()   == m.get_char_size()
        assert m.get_size[int]()      == m.get_int_size()

      # specialized
        if sys.hexversion >= 0x3000000:
            targ = 'long'
        else:
            targ = long
        assert m.get_size[targ]()     == m.get_long_size()

        import ctypes
        assert m.get_size(ctypes.c_double(3.14)) == m.get_size['double']()
        assert m.get_size(ctypes.c_double(3.14).value) == m.get_size['double']()+1

      # auto-instantiation
        assert m.get_size[float]()    == m.get_float_size()
        assert m.get_size['double']() == m.get_double_size()
        assert m.get_size['MyTemplatedMethodClass']() == m.get_self_size()
        assert 'get_size<MyTemplatedMethodClass>' in dir(_cppyy.gbl.MyTemplatedMethodClass)

      # auto through typedef
        assert m.get_size['MyTMCTypedef_t']() == m.get_self_size()
        assert 'get_size<MyTMCTypedef_t>' in dir(_cppyy.gbl.MyTemplatedMethodClass)
        assert m.get_size['MyTemplatedMethodClass']() == m.get_self_size()

    def test02_non_type_template_args(self):
        """Use of non-types as template arguments"""

        import _cppyy

        _cppyy.gbl.gInterpreter.Declare("template<int i> int nt_templ_args() { return i; };")

        assert _cppyy.gbl.nt_templ_args[1]()   == 1
        assert _cppyy.gbl.nt_templ_args[256]() == 256

    def test03_templated_function(self):
        """Templated global and static functions lookup and calls"""

        import _cppyy as cppyy

        # TODO: the following only works if something else has already
        # loaded the headers associated with this template
        ggs = cppyy.gbl.global_get_size
        assert ggs['char']() == 1

        gsf = cppyy.gbl.global_some_foo

        assert gsf[int](3) == 42
        assert gsf(3)      == 42
        assert gsf(3.)     == 42

        gsb = cppyy.gbl.global_some_bar

        assert gsb(3)            == 13
        assert gsb['double'](3.) == 13

        # TODO: the following only works in a namespace
        nsgsb = cppyy.gbl.SomeNS.some_bar

        assert nsgsb[3]
        assert nsgsb[3]() == 3

        # TODO: add some static template method

        # test forced creation of subsequent overloads
        vector = cppyy.gbl.std.vector
        # float in, float out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<float>']
        assert type(ggsr(vector['float']([0.5])).m_retval) == float
        assert ggsr(vector['float']([0.5])).m_retval == 0.5
        # int in, float out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<int>']
        assert type(ggsr(vector['int']([5])).m_retval) == float
        assert ggsr(vector['int']([5])).m_retval == 5.
        # float in, int out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<float>, int']
        assert type(ggsr(vector['float']([0.3])).m_retval) == int
        assert ggsr(vector['float']([0.3])).m_retval == 0
        # int in, int out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<int>, int']
        assert type(ggsr(vector['int']([5])).m_retval) == int
        assert ggsr(vector['int']([5])).m_retval == 5

    def test04_variadic_function(self):
        """Call a variadic function"""

        import _cppyy

        s = _cppyy.gbl.std.ostringstream('(', _cppyy.gbl.std.ios_base.ate)
        # Fails; selects void* overload (?!)
        #s << "("
        _cppyy.gbl.SomeNS.tuplify(s, 1, 4., "aap")
        assert s.str() == "(1, 4, aap, NULL)"

        _cppyy.gbl.gInterpreter.Declare("""
            template<typename... myTypes>
            int test04_variadic_func() { return sizeof...(myTypes); }
        """)

        assert _cppyy.gbl.test04_variadic_func['int', 'double', 'void*']() == 3

    def test05_variadic_overload(self):
        """Call an overloaded variadic function"""

        import _cppyy

        assert _cppyy.gbl.isSomeInt(3.)        == False
        assert _cppyy.gbl.isSomeInt(1)         == True
        assert _cppyy.gbl.isSomeInt()          == False
        assert _cppyy.gbl.isSomeInt(1, 2, 3)   == False

    def test06_variadic_sfinae(self):
        """Attribute testing through SFINAE"""

        import _cppyy
        Obj1             = _cppyy.gbl.AttrTesting.Obj1
        Obj2             = _cppyy.gbl.AttrTesting.Obj2
        has_var1         = _cppyy.gbl.AttrTesting.has_var1
        call_has_var1    = _cppyy.gbl.AttrTesting.call_has_var1

        move = _cppyy.gbl.std.move

        assert has_var1(Obj1()) == hasattr(Obj1(), 'var1')
        assert has_var1(Obj2()) == hasattr(Obj2(), 'var1')
        assert has_var1(3)      == hasattr(3,      'var1')
        assert has_var1("aap")  == hasattr("aap",  'var1')

        assert call_has_var1(move(Obj1())) == True
        assert call_has_var1(move(Obj2())) == False

    def test07_type_deduction(self):
        """Traits/type deduction"""

        import _cppyy
        Obj1                  = _cppyy.gbl.AttrTesting.Obj1
        Obj2                  = _cppyy.gbl.AttrTesting.Obj2
        select_template_arg   = _cppyy.gbl.AttrTesting.select_template_arg

      # assert select_template_arg[0, Obj1, Obj2].argument == Obj1
        assert select_template_arg[1, Obj1, Obj2].argument == Obj2
        raises(TypeError, select_template_arg.__getitem__, 2, Obj1, Obj2)

        # TODO, this doesn't work for builtin types as the 'argument'
        # typedef will not resolve to a class
        #assert select_template_arg[1, int, float].argument == float

    def test08_using_of_static_data(self):
        """Derived class using static data of base"""

        import _cppyy

      # TODO: the following should live in templates.h, but currently fails
      # in TClass::GetListOfMethods()
        _cppyy.gbl.gInterpreter.Declare("""
        template <typename T> struct BaseClassWithStatic {
            static T const ref_value;
        };

        template <typename T>
        T const BaseClassWithStatic<T>::ref_value = 42;

        template <typename T>
        struct DerivedClassUsingStatic : public BaseClassWithStatic<T> {
            using BaseClassWithStatic<T>::ref_value;

            explicit DerivedClassUsingStatic(T x) : BaseClassWithStatic<T>() {
                m_value = x > ref_value ? ref_value : x;
            }

            T m_value;
        };""")


      # TODO: the ref_value property is inaccessible (offset == -1)
      # assert _cppyy.gbl.BaseClassWithStatic["size_t"].ref_value == 42

        b1 = _cppyy.gbl.DerivedClassUsingStatic["size_t"](  0)
        b2 = _cppyy.gbl.DerivedClassUsingStatic["size_t"](100)

      # assert b1.ref_value == 42
        assert b1.m_value   ==  0

      # assert b2.ref_value == 42
        assert b2.m_value   == 42


class AppTestBOOSTANY:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_templates = cls.space.appexec([], """():
            import ctypes, _cppyy
            _cppyy._post_import_startup()""")

    def test01_any_class(self):
        """Usage of boost::any"""

        import _cppyy

        if not _cppyy.gbl.gInterpreter.Declare('#include "boost/any.hpp"'):
            import warnings
            warnings.warn('skipping boost/any testing')
            return

        assert _cppyy.gbl.boost
        assert _cppyy.gbl.boost.any

        std, boost = _cppyy.gbl.std, _cppyy.gbl.boost

        assert std.list[boost.any]

        val = boost.any()
        # test both by-ref and by rvalue
        v = std.vector[int]()
        val.__assign__(v)
        val.__assign__(std.move(std.vector[int](range(100))))

        _cppyy.gbl.gInterpreter.ProcessLine(
            "namespace _cppyy_internal { auto* stdvectid = &typeid(std::vector<int>); }")

        assert val.type() == _cppyy.gbl._cppyy_internal.stdvectid

        extract = boost.any_cast[std.vector[int]](val)
        assert type(extract) is std.vector[int]
        assert len(extract) == 100
        extract += range(100)
        assert len(extract) == 200

        val.__assign__(std.move(extract))   # move forced

        # TODO: we hit boost::any_cast<int>(boost::any* operand) instead
        # of the reference version which raises
        boost.any_cast.__useffi__ = False
        try:
          # raises(Exception, boost.any_cast[int], val)
            assert not boost.any_cast[int](val)
        except Exception:
          # getting here is good, too ...
            pass

        extract = boost.any_cast[std.vector[int]](val)
        assert len(extract) == 200
