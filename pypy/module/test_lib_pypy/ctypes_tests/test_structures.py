from ctypes import *
from struct import calcsize
from support import BaseCTypesTestChecker

import py

class TestSubclasses(BaseCTypesTestChecker):
    def test_subclass(self):
        class X(Structure):
            _fields_ = [("a", c_int)]

        class Y(X):
            _fields_ = [("b", c_int)]

        class Z(X):
            pass

        assert sizeof(X) == sizeof(c_int)
        assert sizeof(Y) == sizeof(c_int)*2
        assert sizeof(Z) == sizeof(c_int)
        assert X._fields_ == [("a", c_int)]
        assert Y._fields_ == [("b", c_int)]
        assert Z._fields_ == [("a", c_int)]

        assert Y._names == ['a', 'b']

    def test_subclass_delayed(self):
        class X(Structure):
            pass
        assert sizeof(X) == 0
        X._fields_ = [("a", c_int)]

        class Y(X):
            pass
        assert sizeof(Y) == sizeof(X)
        Y._fields_ = [("b", c_int)]

        class Z(X):
            pass

        assert sizeof(X) == sizeof(c_int)
        assert sizeof(Y) == sizeof(c_int)*2
        assert sizeof(Z) == sizeof(c_int)
        assert X._fields_ == [("a", c_int)]
        assert Y._fields_ == [("b", c_int)]
        assert Z._fields_ == [("a", c_int)]

class TestStructure(BaseCTypesTestChecker):
    formats = {"c": c_char,
               "b": c_byte,
               "B": c_ubyte,
               "h": c_short,
               "H": c_ushort,
               "i": c_int,
               "I": c_uint,
               "l": c_long,
               "L": c_ulong,
               "q": c_longlong,
               "Q": c_ulonglong,
               "f": c_float,
               "d": c_double,
               }

    def test_simple_structs(self):
        for code, tp in self.formats.items():
            class X(Structure):
                _fields_ = [("x", c_char),
                            ("y", tp)]
            assert (sizeof(X), code) == (
                                 (calcsize("c%c" % (code,)), code))

    def test_unions(self):
        for code, tp in self.formats.items():
            class X(Union):
                _fields_ = [("x", c_char),
                            ("y", tp)]
            assert (sizeof(X), code) == (
                                 (calcsize("%c" % (code)), code))

    def test_struct_alignment(self):
        class X(Structure):
            _fields_ = [("x", c_char * 3)]
        assert alignment(X) == calcsize("s")
        assert sizeof(X) == calcsize("3s")

        class Y(Structure):
            _fields_ = [("x", c_char * 3),
                        ("y", c_int)]
        assert alignment(Y) == calcsize("i")
        assert sizeof(Y) == calcsize("3si")

        class SI(Structure):
            _fields_ = [("a", X),
                        ("b", Y)]
        assert alignment(SI) == max(alignment(Y), alignment(X))
        assert sizeof(SI) == calcsize("3s0i 3si 0i")

        class IS(Structure):
            _fields_ = [("b", Y),
                        ("a", X)]

        assert alignment(SI) == max(alignment(X), alignment(Y))
        assert sizeof(IS) == calcsize("3si 3s 0i")

        class XX(Structure):
            _fields_ = [("a", X),
                        ("b", X)]
        assert alignment(XX) == alignment(X)
        assert sizeof(XX) == calcsize("3s 3s 0s")

    def test_emtpy(self):
        # I had problems with these
        #
        # Although these are patological cases: Empty Structures!
        class X(Structure):
            _fields_ = []

        class Y(Union):
            _fields_ = []

        # Is this really the correct alignment, or should it be 0?
        assert alignment(X) == alignment(Y) == 1
        assert sizeof(X) == sizeof(Y) == 0

        class XX(Structure):
            _fields_ = [("a", X),
                        ("b", X)]

        assert alignment(XX) == 1
        assert sizeof(XX) == 0

    def test_fields(self):
        # test the offset and size attributes of Structure/Unoin fields.
        class X(Structure):
            _fields_ = [("x", c_int),
                        ("y", c_char)]

        assert X.x.offset == 0
        assert X.x.size == sizeof(c_int)

        assert X.y.offset == sizeof(c_int)
        assert X.y.size == sizeof(c_char)

        # readonly
        raises((TypeError, AttributeError), setattr, X.x, "offset", 92)
        raises((TypeError, AttributeError), setattr, X.x, "size", 92)

        class X(Union):
            _fields_ = [("x", c_int),
                        ("y", c_char)]

        assert X.x.offset == 0
        assert X.x.size == sizeof(c_int)

        assert X.y.offset == 0
        assert X.y.size == sizeof(c_char)

        # readonly
        raises((TypeError, AttributeError), setattr, X.x, "offset", 92)
        raises((TypeError, AttributeError), setattr, X.x, "size", 92)

        # XXX Should we check nested data types also?
        # offset is always relative to the class...

    def test_packed(self):
        py.test.skip("custom alignment not supported")
        class X(Structure):
            _fields_ = [("a", c_byte),
                        ("b", c_longlong)]
            _pack_ = 1

        assert sizeof(X) == 9
        assert X.b.offset == 1

        class X(Structure):
            _fields_ = [("a", c_byte),
                        ("b", c_longlong)]
            _pack_ = 2
        assert sizeof(X) == 10
        assert X.b.offset == 2

        class X(Structure):
            _fields_ = [("a", c_byte),
                        ("b", c_longlong)]
            _pack_ = 4
        assert sizeof(X) == 12
        assert X.b.offset == 4

        import struct
        longlong_size = struct.calcsize("q")
        longlong_align = struct.calcsize("bq") - longlong_size

        class X(Structure):
            _fields_ = [("a", c_byte),
                        ("b", c_longlong)]
            _pack_ = 8

        assert sizeof(X) == longlong_align + longlong_size
        assert X.b.offset == min(8, longlong_align)


        d = {"_fields_": [("a", "b"),
                          ("b", "q")],
             "_pack_": -1}
        raises(ValueError, type(Structure), "X", (Structure,), d)

    def test_initializers(self):
        class Person(Structure):
            _fields_ = [("name", c_char*6),
                        ("age", c_int)]

        raises(TypeError, Person, 42)
        raises(ValueError, Person, "asldkjaslkdjaslkdj")
        raises(TypeError, Person, "Name", "HI")

        # short enough
        assert Person("12345", 5).name == "12345"
        # exact fit
        assert Person("123456", 5).name == "123456"
        # too long
        raises(ValueError, Person, "1234567", 5)


    def test_keyword_initializers(self):
        class POINT(Structure):
            _fields_ = [("x", c_int), ("y", c_int)]
        pt = POINT(1, 2)
        assert (pt.x, pt.y) == (1, 2)

        pt = POINT(y=2, x=1)
        assert (pt.x, pt.y) == (1, 2)

    def test_invalid_field_types(self):
        class POINT(Structure):
            pass
        raises(TypeError, setattr, POINT, "_fields_", [("x", 1), ("y", 2)])

    def test_intarray_fields(self):
        class SomeInts(Structure):
            _fields_ = [("a", c_int * 4)]

        # can use tuple to initialize array (but not list!)
        assert SomeInts((1, 2)).a[:] == [1, 2, 0, 0]
        assert SomeInts((1, 2, 3, 4)).a[:] == [1, 2, 3, 4]
        # too long
        # XXX Should raise ValueError?, not RuntimeError
        raises(RuntimeError, SomeInts, (1, 2, 3, 4, 5))

    def test_nested_initializers(self):
        # test initializing nested structures
        class Phone(Structure):
            _fields_ = [("areacode", c_char*6),
                        ("number", c_char*12)]

        class Person(Structure):
            _fields_ = [("name", c_char * 12),
                        ("phone", Phone),
                        ("age", c_int)]

        p = Person("Someone", ("1234", "5678"), 5)

        assert p.name == "Someone"
        assert p.phone.areacode == "1234"
        assert p.phone.number == "5678"
        assert p.age == 5

    def test_structures_with_wchar(self):
        py.test.skip("need unicode support on _rawffi level")
        try:
            c_wchar
        except NameError:
            return # no unicode

        class PersonW(Structure):
            _fields_ = [("name", c_wchar * 12),
                        ("age", c_int)]

        p = PersonW(u"Someone")
        assert p.name == "Someone"

        assert PersonW(u"1234567890").name == u"1234567890"
        assert PersonW(u"12345678901").name == u"12345678901"
        # exact fit
        assert PersonW(u"123456789012").name == u"123456789012"
        #too long
        raises(ValueError, PersonW, u"1234567890123")

    def test_init_errors(self):
        py.test.skip("not implemented error details")
        class Phone(Structure):
            _fields_ = [("areacode", c_char*6),
                        ("number", c_char*12)]

        class Person(Structure):
            _fields_ = [("name", c_char * 12),
                        ("phone", Phone),
                        ("age", c_int)]

        cls, msg = self.get_except(Person, "Someone", (1, 2))
        assert cls == RuntimeError
        # In Python 2.5, Exception is a new-style class, and the repr changed
        if issubclass(Exception, object):
            assert msg == (
                                 "(Phone) <type 'exceptions.TypeError'>: "
                                 "expected string or Unicode object, int found")
        else:
            assert msg == (
                                 "(Phone) exceptions.TypeError: "
                                 "expected string or Unicode object, int found")

        cls, msg = self.get_except(Person, "Someone", ("a", "b", "c"))
        assert cls == RuntimeError
        if issubclass(Exception, object):
            assert msg == (
                                 "(Phone) <type 'exceptions.ValueError'>: too many initializers")
        else:
            assert msg == "(Phone) exceptions.ValueError: too many initializers"


    def get_except(self, func, *args):
        # XXX remove this, py.test.raises returns a nice inspectable object
        try:
            func(*args)
        except Exception, detail:
            return detail.__class__, str(detail)


##    def test_subclass_creation(self):
##        meta = type(Structure)
##        # same as 'class X(Structure): pass'
##        # fails, since we need either a _fields_ or a _abstract_ attribute
##        cls, msg = self.get_except(meta, "X", (Structure,), {})
##        self.failUnlessEqual((cls, msg),
##                             (AttributeError, "class must define a '_fields_' attribute"))

    def test_abstract_class(self):
        py.test.skip("_abstract_ semantics not implemented")
        class X(Structure):
            _abstract_ = "something"
        # try 'X()'
        cls, msg = self.get_except(eval, "X()", locals())
        assert (cls, msg) == (TypeError, "abstract class")

    def test_methods(self):
##        class X(Structure):
##            _fields_ = []

        assert "in_dll" in dir(type(Structure))
        assert "from_address" in dir(type(Structure))
        assert "in_dll" in dir(type(Structure))

    def test_fields_is_a_tuple(self):
        class Person(Structure):
            _fields_ = (("name", c_char*6),
                        ("age", c_int))

        # short enough
        p = Person("123456", 6)
        assert p.name == "123456"
        assert p.age == 6

    def test_subclassing_field_is_a_tuple(self):
        py.test.skip("subclassing semantics not implemented")
        class Person(Structure):
            _fields_ = (("name", c_char*6),
                        ("age", c_int))
        class PersonWithIncome(Person):
            _fields_ = [("income", c_int)]

        # short enough
        p = PersonWithIncome("123456", 6, 5)
        assert p.name == "123456"
        assert p.age == 6
        assert p.income == 5

    def test___init__(self):
        class Person(Structure):
            _fields_ = (("name", c_char*10),
                        ("age", c_int))

            def __init__(self, name, surname, age):
                self.name = name + ' ' + surname
                self.age = age

        p = Person("John", "Doe", 25)
        assert p.name == "John Doe"
        assert p.age == 25

    def test_setattr(self):
        class X(Structure):
            _fields_ = [("a", c_int)]

        x = X()
        x.other = 42
        assert x.other == 42

    def test_withslots(self):
        class X(Structure):
            _fields_ = [("a", c_int * 2)]
            __slots__ = ['a']

        x = X()
        x.a = (42, 43)
        assert tuple(x.a) == (42, 43)

    def test_getattr_recursion(self):
        # Structure.__getattr__ used to call itself recursively
        # and hit the recursion limit.
        import sys
        events = []

        def tracefunc(frame, event, arg):
            funcname = frame.f_code.co_name
            if 'getattr' in funcname:
                events.append(funcname)

        oldtrace = sys.settrace(tracefunc)
        try:
            class X(Structure):
                _fields_ = [("a", c_int)]

            assert len(events) < 20
        finally:
            sys.settrace(oldtrace)
            events = None

class TestPointerMember(BaseCTypesTestChecker):

    def test_1(self):
        # a Structure with a POINTER field
        class S(Structure):
            _fields_ = [("array", POINTER(c_int))]

        s = S()
        # We can assign arrays of the correct type
        s.array = (c_int * 3)(1, 2, 3)
        items = [s.array[i] for i in range(3)]
        assert items == [1, 2, 3]

        # The following are bugs, but are included here because the unittests
        # also describe the current behaviour.
        #
        # This fails with SystemError: bad arg to internal function
        # or with IndexError (with a patch I have)

        s.array[0] = 42

        items = [s.array[i] for i in range(3)]
        assert items == [42, 2, 3]

        s.array[0] = 1

##        s.array[1] = 42

        items = [s.array[i] for i in range(3)]
        assert items == [1, 2, 3]

    def test_none_to_pointer_fields(self):
        class S(Structure):
            _fields_ = [("x", c_int),
                        ("p", POINTER(c_int))]

        s = S()
        s.x = 12345678
        s.p = None
        assert s.x == 12345678


class TestRecursiveStructure(BaseCTypesTestChecker):
    def test_contains_itself(self):
        class Recursive(Structure):
            pass

        try:
            Recursive._fields_ = [("next", Recursive)]
        except AttributeError, details:
            assert ("Structure or union cannot contain itself" in
                            str(details))
        else:
            raise AssertionError, "Structure or union cannot contain itself"


    def test_vice_versa(self):
        py.test.skip("mutually dependent lazily defined structures error semantics")
        class First(Structure):
            pass
        class Second(Structure):
            pass

        First._fields_ = [("second", Second)]

        try:
            Second._fields_ = [("first", First)]
        except AttributeError, details:
            assert ("_fields_ is final" in
                            str(details))
        else:
            raise AssertionError, "AttributeError not raised"

    def test_nonfinal_struct(self):
        class X(Structure):
            pass
        assert sizeof(X) == 0
        X._fields_ = [("a", c_int),]
        raises(AttributeError, setattr, X, "_fields_", [])

        class X(Structure):
            pass
        X()
        raises(AttributeError, setattr, X, "_fields_", [])

        class X(Structure):
            pass
        class Y(X):
            pass
        raises(AttributeError, setattr, X, "_fields_", [])
        Y.__fields__ = []

class TestPatologicalCases(BaseCTypesTestChecker):
    def test_structure_overloading_getattr(self):
        class X(Structure):
            _fields_ = [('x', c_int)]

            def __getattr__(self, name):
                raise AttributeError, name

        x = X()
        assert x.x == 0

