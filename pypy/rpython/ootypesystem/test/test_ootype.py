from pypy.rpython.ootypesystem.ootype import *
import py

def test_simple():
    assert typeOf(1) is Signed

def test_class_hash():
    M = Meth([Signed], Signed)
    def m_(self, b):
       return self.a + b
    m = meth(M, _name="m", _callable=m_)
    I = Instance("test", None, {"a": Signed}, {"m": m})
    assert type(hash(I)) == int

def test_simple_class():
    I = Instance("test", None, {"a": Signed})
    i = new(I)

    py.test.raises(TypeError, "i.z")
    py.test.raises(TypeError, "i.a = 3.0")

    i.a = 3
    assert i.a == 3

def test_assign_super_attr():
    C = Instance("test", None, {"a": (Signed, 3)})
    D = Instance("test2", C, {})

    d = new(D)

    d.a = 1

    assert d.a == 1

def test_runtime_instanciation():
    I = Instance("test", None, {"a": Signed})
    c = runtimeClass(I)
    i = runtimenew(c)

    assert typeOf(i) == I
    assert typeOf(c) == Class

def test_classof():
    I = Instance("test", None, {"a": Signed})
    c = runtimeClass(I)
    i = new(I)

    assert classof(i) == c

    j = new(I)

    assert classof(i) is classof(j)
    I2 = Instance("test2", I, {"b": Signed})
    i2 = new(I2)
    assert classof(i2) is not classof(i)
    assert classof(i2) != classof(i)
    
def test_simple_default_class():
    I = Instance("test", None, {"a": (Signed, 3)})
    i = new(I)

    assert i.a == 3

    py.test.raises(TypeError, "Instance('test', None, {'a': (Signed, 3.0)})")

def test_simple_null():
    C = Instance("test", None, {"a": Signed})

    c = null(C)
    assert typeOf(c) == C

    py.test.raises(RuntimeError, "c.a")

def test_simple_class_field():
    C = Instance("test", None, {})

    D = Instance("test2", None, {"a": C})
    d = new(D)

    assert typeOf(d.a) == C

    assert d.a == null(C)

def test_simple_recursive_class():
    C = Instance("test", None, {})

    addFields(C, {"inst": C})

    c = new(C)
    assert c.inst == null(C)

def test_simple_super():
    C = Instance("test", None, {"a": (Signed, 3)})
    D = Instance("test2", C, {})

    d = new(D)
    assert d.a == 3

def test_simple_field_shadowing():
    C = Instance("test", None, {"a": (Signed, 3)})
    
    py.test.raises(TypeError, """D = Instance("test2", C, {"a": (Signed, 3)})""")

def test_simple_static_method():
    F = StaticMethod([Signed, Signed], Signed)
    def f_(a, b):
       return a+b
    f = static_meth(F, "f", _callable=f_)
    assert typeOf(f) == F

    result = f(2, 3)
    assert typeOf(result) == Signed
    assert result == 5

def test_static_method_args():
    F = StaticMethod([Signed, Signed], Signed)
    def f_(a, b):
       return a+b
    f = static_meth(F, "f", _callable=f_)

    py.test.raises(TypeError, "f(2.0, 3.0)")
    py.test.raises(TypeError, "f()")
    py.test.raises(TypeError, "f(1, 2, 3)")

def test_class_method():
    M = Meth([Signed], Signed)
    def m_(self, b):
       return self.a + b
    m = meth(M, _name="m", _callable=m_)

    C = Instance("test", None, {"a": (Signed, 2)}, {"m": m})
    c = new(C)

    assert c.m(3) == 5

    py.test.raises(TypeError, "c.m(3.0)")
    py.test.raises(TypeError, "c.m()")
    py.test.raises(TypeError, "c.m(1, 2, 3)")

def test_class_method_field_clash():
    M = Meth([Signed], Signed)
    def m_(self, b):
       return self.a + b
    m = meth(M, _name="m", _callable=m_)

    py.test.raises(TypeError, """Instance("test", None, {"a": M})""")

    py.test.raises(TypeError, """Instance("test", None, {"m": Signed}, {"m":m})""")

def test_simple_recursive_meth():
    C = Instance("test", None, {"a": (Signed, 3)})

    M = Meth([C], Signed)
    def m_(self, other):
       return self.a + other.a
    m = meth(M, _name="m", _callable=m_)

    addMethods(C, {"m": m})
    c = new(C)

    assert c.m(c) == 6

def test_explicit_name_clash():
    C = Instance("test", None, {})

    addFields(C, {"a": (Signed, 3)})

    M = Meth([Signed], Signed)
    m = meth(M, _name="m")

    py.test.raises(TypeError, """addMethods(C, {"a": m})""")

    addMethods(C, {"b": m})

    py.test.raises(TypeError, """addFields(C, {"b": Signed})""")

def test_instanceof():
    C = Instance("test", None, {})
    D = Instance("test2", C, {})
    c = new(C)
    d = new(D)
    assert instanceof(c, C)
    assert instanceof(d, D)
    assert not instanceof(c, D)
    assert instanceof(d, C)

def test_superclass_meth_lookup():
    C = Instance("test", None, {"a": (Signed, 3)})

    M = Meth([C], Signed)
    def m_(self, other):
       return self.a + other.a
    m = meth(M, _name="m", _callable=m_)

    addMethods(C, {"m": m})

    D = Instance("test2", C, {})
    d = new(D)

    assert d.m(d) == 6

    def m_(self, other):
       return self.a * other.a
    m = meth(M, _name="m", _callable=m_)
    addMethods(D, {"m": m})

    d = new(D)
    assert d.m(d) == 9

def test_isSubclass():
    A = Instance("A", None)
    B = Instance("B", A)
    C = Instance("C", A)
    D = Instance("D", C)

    assert isSubclass(A, A)
    assert isSubclass(B, A)
    assert isSubclass(C, A)
    assert not isSubclass(A, B)
    assert not isSubclass(B, C)
    assert isSubclass(D, C)
    assert isSubclass(D, A)
    assert not isSubclass(D, B)
    
def test_commonBaseclass():
    A = Instance("A", None)
    B = Instance("B", A)
    C = Instance("C", A)
    D = Instance("D", C)
    E = Instance("E", None)
    F = Instance("F", E)

    assert commonBaseclass(A, A) == A
    assert commonBaseclass(A, B) == A
    assert commonBaseclass(B, A) == A
    assert commonBaseclass(B, B) == B
    assert commonBaseclass(B, C) == A
    assert commonBaseclass(C, B) == A
    assert commonBaseclass(C, A) == A
    assert commonBaseclass(D, A) == A
    assert commonBaseclass(D, B) == A
    assert commonBaseclass(D, C) == C
    assert commonBaseclass(A, D) == A
    assert commonBaseclass(B, D) == A
    assert commonBaseclass(C, D) == C
    
    assert commonBaseclass(E, A) is None
    assert commonBaseclass(E, B) is None
    assert commonBaseclass(F, A) is None
    
def test_equality():
    A = Instance("A", None)
    B = Instance("B", A)
    a1 = new(A)
    a2 = new(A)
    b1 = new(B)
    az = null(A)
    bz = null(B)
    assert a1
    assert a2
    assert not az
    assert not bz
    result = []
    for first in [a1, a2, b1, az, bz]:
        for second in [a1, a2, b1, az, bz]:
            eq = first == second
            assert (first != second) == (not eq)
            result.append(eq)
    assert result == [
        1, 0, 0, 0, 0,
        0, 1, 0, 0, 0,
        0, 0, 1, 0, 0,
        0, 0, 0, 1, 1,
        0, 0, 0, 1, 1,
        ]

def test_subclassof():
    A = Instance("A", None)
    B = Instance("B", A)
    C = Instance("C", B)
    result = []
    for first in [A, B, C]:
        for second in [A, B, C]:
            result.append(subclassof(runtimeClass(first),
                                     runtimeClass(second)))
    assert result == [
        1, 0, 0,
        1, 1, 0,
        1, 1, 1,
        ]
