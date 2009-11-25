from pypy.rpython.ootypesystem.ootype import *
import py

def test_simple():
    assert typeOf(1) is Signed

def test_class_hash():
    M = Meth([Signed], Signed)
    def m_(self, b):
       return self.a + b
    m = meth(M, _name="m", _callable=m_)
    I = Instance("test", ROOT, {"a": Signed}, {"m": m})
    assert type(hash(I)) == int

def test_simple_class():
    I = Instance("test", ROOT, {"a": Signed})
    i = new(I)

    py.test.raises(TypeError, "i.z")
    py.test.raises(TypeError, "i.a = 3.0")

    i.a = 3
    assert i.a == 3

def test_assign_super_attr():
    C = Instance("test", ROOT, {"a": (Signed, 3)})
    D = Instance("test2", C, {})

    d = new(D)

    d.a = 1

    assert d.a == 1

def test_runtime_instantiation():
    I = Instance("test", ROOT, {"a": Signed})
    c = runtimeClass(I)
    i = runtimenew(c)

    assert typeOf(i) == I
    assert typeOf(c) == Class

def test_runtime_record_instantiation():
    R = Record({"a": Signed})
    c = runtimeClass(R)
    r = runtimenew(c)

    assert typeOf(r) == R
    assert typeOf(c) == Class

def test_class_records():
    R1 = Record({"a": Signed})
    R2 = Record({"a": Signed})
    assert R1 == R2
    assert runtimeClass(R1) is runtimeClass(R2)

def test_class_builtintype():
    L1 = List(Signed)
    L2 = List(Signed)
    assert L1 == L2
    assert runtimeClass(L1) is runtimeClass(L2)

def test_class_class():
    L = List(Signed)
    R = Record({"a": Signed})
    c1 = runtimeClass(L)
    c2 = runtimeClass(R)
    C1 = typeOf(c1)
    C2 = typeOf(c2)
    assert runtimeClass(C1) is runtimeClass(C2)

def test_classof():
    I = Instance("test", ROOT, {"a": Signed})
    c = runtimeClass(I)
    i = new(I)

    assert classof(i) == c

    j = new(I)

    assert classof(i) is classof(j)
    I2 = Instance("test2", I, {"b": Signed})
    i2 = new(I2)
    assert classof(i2) is not classof(i)
    assert classof(i2) != classof(i)
    
def test_dynamictype():
    A = Instance("A", ROOT)
    B = Instance("B", A)
    a = new(A)
    b = new(B)
    assert dynamicType(a) is A
    assert dynamicType(b) is B

    b = ooupcast(A, b)
    assert dynamicType(b) is B

def test_simple_default_class():
    I = Instance("test", ROOT, {"a": (Signed, 3)})
    i = new(I)

    assert i.a == 3

    py.test.raises(TypeError, "Instance('test', ROOT, {'a': (Signed, 3.0)})")

def test_overridden_default():
    A = Instance("A", ROOT, {"a": (Signed, 3)})
    B = Instance("B", A)
    overrideDefaultForFields(B, {"a": (Signed, 5)})

    b = new(B)
    assert b.a == 5

def test_simple_null():
    C = Instance("test", ROOT, {"a": Signed})

    c = null(C)
    assert typeOf(c) == C

    py.test.raises(RuntimeError, "c.a")

def test_simple_class_field():
    C = Instance("test", ROOT, {})

    D = Instance("test2", ROOT, {"a": C})
    d = new(D)

    assert typeOf(d.a) == C

    assert d.a == null(C)

def test_simple_recursive_class():
    C = Instance("test", ROOT, {})

    addFields(C, {"inst": C})

    c = new(C)
    assert c.inst == null(C)

def test_simple_super():
    C = Instance("test", ROOT, {"a": (Signed, 3)})
    D = Instance("test2", C, {})

    d = new(D)
    assert d.a == 3

def test_simple_field_shadowing():
    C = Instance("test", ROOT, {"a": (Signed, 3)})
    
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

    null_F = null(F)
    py.test.raises(RuntimeError, "null_F(1,2)")

def test_class_method():
    M = Meth([Signed], Signed)
    def m_(self, b):
       return self.a + b
    m = meth(M, _name="m", _callable=m_)

    C = Instance("test", ROOT, {"a": (Signed, 2)}, {"m": m})
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

    py.test.raises(TypeError, """Instance("test", ROOT, {"a": M})""")

    py.test.raises(TypeError, """Instance("test", ROOT, {"m": Signed}, {"m":m})""")

def test_simple_recursive_meth():
    C = Instance("test", ROOT, {"a": (Signed, 3)})

    M = Meth([C], Signed)
    def m_(self, other):
       return self.a + other.a
    m = meth(M, _name="m", _callable=m_)

    addMethods(C, {"m": m})
    c = new(C)

    assert c.m(c) == 6

def test_overloaded_method():
    C = Instance("test", ROOT, {'a': (Signed, 3)})
    def m1(self, x):
        return self.a+x
    def m2(self, x, y):
        return self.a+x+y
    def m3(self, x):
        return self.a*x
    m = overload(meth(Meth([Signed], Signed), _callable=m1, _name='m'),
                 meth(Meth([Signed, Signed], Signed), _callable=m2, _name='m'),
                 meth(Meth([Float], Float), _callable=m3, _name='m'))
    addMethods(C, {"m": m})
    c = new(C)
    assert c.m(1) == 4
    assert c.m(2, 3) == 8
    assert c.m(2.0) == 6

def test_overloaded_method_upcast():
    def m(self, dummy):
        return 42
    C = Instance("base", ROOT, {}, {
        'foo': overload(meth(Meth([ROOT], String), _callable=m))})
    c = new(C)
    assert c.foo(c) == 42

def test_method_selftype():
    LIST = List(Signed)
    _, meth = LIST._lookup('ll_setitem_fast')
    METH = typeOf(meth)
    assert METH.SELFTYPE is LIST

def test_bound_method_name():
    LIST = List(Signed)
    lst = new(LIST)
    meth = lst.ll_getitem_fast
    assert meth._name == 'll_getitem_fast'

def test_explicit_name_clash():
    C = Instance("test", ROOT, {})

    addFields(C, {"a": (Signed, 3)})

    M = Meth([Signed], Signed)
    m = meth(M, _name="m")

    py.test.raises(TypeError, """addMethods(C, {"a": m})""")

    addMethods(C, {"b": m})

    py.test.raises(TypeError, """addFields(C, {"b": Signed})""")

def test_instanceof():
    C = Instance("test", ROOT, {})
    D = Instance("test2", C, {})
    c = new(C)
    d = new(D)
    assert instanceof(c, C)
    assert instanceof(d, D)
    assert not instanceof(c, D)
    assert instanceof(d, C)

def test_superclass_meth_lookup():
    C = Instance("test", ROOT, {"a": (Signed, 3)})

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
    A = Instance("A", ROOT)
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
    A = Instance("A", ROOT)
    B = Instance("B", A)
    C = Instance("C", A)
    D = Instance("D", C)
    E = Instance("E", ROOT)
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
    
    assert commonBaseclass(E, A) is ROOT
    assert commonBaseclass(E, B) is ROOT
    assert commonBaseclass(F, A) is ROOT
    
def test_equality():
    A = Instance("A", ROOT)
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
    A = Instance("A", ROOT)
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

def test_static_method_equality():
    SM = StaticMethod([], Signed)
    SM1 = StaticMethod([], Signed)
    assert SM == SM1

    sm = static_meth(SM, 'f', graph='graph')
    sm1 = static_meth(SM1, 'f', graph='graph')
    assert sm == sm1

def test_casts():
    A = Instance('A', ROOT)
    B = Instance('B', A)
    b = new(B)
    assert instanceof(b, B)
    assert instanceof(b, A)
    assert typeOf(b) == B
    bA = ooupcast(A, b)
    assert instanceof(bA, B)
    if STATICNESS:
        assert typeOf(bA) == A
    bB = oodowncast(B, bA)
    assert instanceof(bB, A)
    assert instanceof(bB, B)
    assert typeOf(bB) == B

def test_visibility():
    if not STATICNESS:
        py.test.skip("static types not enforced in ootype")
    M = Meth([], Signed)
    def mA_(a):
        return 1
    def mB_(b):
        return 2
    def nB_(b):
        return 3
    mA = meth(M, name="m", _callable=mA_)
    mB = meth(M, name="m", _callable=mB_)
    nB = meth(M, name="n", _callable=nB_)
    A = Instance('A', ROOT, {}, {'m': mA})
    B = Instance('B', A, {}, {'m': mB, 'n': nB})
    b = new(B)
    assert b.m() == 2
    assert b.n() == 3
    bA = ooupcast(A, b)
    assert bA.m() == 2
    py.test.raises(TypeError, "bA.n()")
    assert oodowncast(B, bA).n() == 3
    M = Meth([A], Signed)
    def xA_(slf, a):
        return a.n()
    xA = meth(M, name="x", _callable=xA_)
    addMethods(A, {'x': xA})
    a = new(A)
    py.test.raises(TypeError, "a.x(b)")
    def yA_(slf, a):
        if instanceof(a, B):
            return oodowncast(B, a).n()
        return a.m()
    yA = meth(M, name="y", _callable=yA_)
    addMethods(A, {'y': yA})
    assert a.y(a) == 1
    assert a.y(b) == 3
    #
    M = Meth([], Signed)
    def zA_(slf):
        return slf.n()
    zA = meth(M, name="z", _callable=zA_)
    addMethods(A, {'z': zA})
    py.test.raises(TypeError, "b.z()")
    def zzA_(slf):
        if instanceof(slf, B):
            return oodowncast(B, slf).n()
        return slf.m()
    zzA = meth(M, name="zz", _callable=zzA_)
    addMethods(A, {'zz': zzA})
    assert a.zz() == 1
    assert b.zz() == 3

def test_view_instance_hash():
    I = Instance("Foo", ROOT)

    inst = new(I)
    inst_up = ooupcast(ROOT, inst)
    inst_up2 = ooupcast(ROOT, inst)

    assert inst_up == inst_up2
    assert hash(inst_up) == hash(inst_up2)

def test_instance_equality():
    A = Instance("Foo", ROOT)
    B = Instance("Foo", ROOT)
    # Instance compares by reference
    assert not A == B
    assert A != B 

def test_subclasses():
    A = Instance("A", ROOT)
    B = Instance("B", A)
    C = Instance("C", A)
    D = Instance("D", C)

    assert A in ROOT._subclasses
    assert B in A._subclasses
    assert not B._subclasses
    assert C in A._subclasses
    assert D in C._subclasses

def test_canraise():
    LT = List(Signed)
    _, meth = LT._lookup('ll_length')
    assert meth._can_raise == False
    DT = DictItemsIterator(String, Signed)
    _, meth = DT._lookup('ll_go_next')
    assert meth._can_raise == True

def test_cast_null():
    A = Instance("A", ROOT)
    B = Instance("B", ROOT)
    rootnull = null(ROOT)
    anull = oodowncast(A, rootnull)
    assert typeOf(anull) is A
    assert ooupcast(ROOT, anull) == rootnull
    py.test.raises(AssertionError, oodowncast, B, anull)

def test_weak_reference():
    import gc
    A = Instance("A", ROOT)
    obj = new(A)
    ref = new(WeakReference)
    ref.ll_set(obj)
    assert oodowncast(A, ref.ll_deref()) == obj
    del obj
    gc.collect()
    assert ref.ll_deref() is null(ROOT)

def test_dead_wref():
    ref = new(WeakReference)
    assert ref.ll_deref() is null(ROOT)


# we use the translator for this test because it's much easier to get
# a class hierarchy with methods and graphs by using it than
# constructing it by hand
def test_lookup_graphs():
    from pypy.translator.translator import TranslationContext, graphof
    class A:
        def foo(self):
            pass
        def bar(self):
            pass

    class B(A):
        def foo(self):
            pass

    def fn(flag):
        obj = flag and A() or B()
        obj.foo()
        obj.bar()
        return obj

    t = TranslationContext()
    t.buildannotator().build_types(fn, [int])
    t.buildrtyper(type_system='ootype').specialize()
    graph = graphof(t, fn)
    TYPE_A = graph.getreturnvar().concretetype
    TYPE_B = TYPE_A._subclasses[0]
    assert len(TYPE_A._lookup_graphs('ofoo')) == 2
    assert len(TYPE_B._lookup_graphs('ofoo')) == 1
    assert len(TYPE_A._lookup_graphs('obar')) == 1
    assert len(TYPE_B._lookup_graphs('obar')) == 1

def test_lookup_graphs_abstract():
    from pypy.translator.translator import TranslationContext, graphof
    class A:
        pass
    class B(A):
        def foo(self):
            pass
    class C(A):
        def foo(self):
            pass

    def fn(flag):
        obj = flag and B() or C()
        obj.foo()
        return obj

    t = TranslationContext()
    t.buildannotator().build_types(fn, [int])
    t.buildrtyper(type_system='ootype').specialize()
    graph = graphof(t, fn)
    TYPE_A = graph.getreturnvar().concretetype
    TYPE_B = TYPE_A._subclasses[0]
    TYPE_C = TYPE_A._subclasses[1]
    assert len(TYPE_A._lookup_graphs('ofoo')) == 2
    assert len(TYPE_B._lookup_graphs('ofoo')) == 1
    assert len(TYPE_C._lookup_graphs('ofoo')) == 1

def test_cast_object_instance():
    A = Instance("Foo", ROOT)
    a = new(A)
    obj = cast_to_object(a)
    assert typeOf(obj) is Object
    assert cast_from_object(A, obj) == a
    a2 = cast_from_object(ROOT, obj)
    assert typeOf(a2) is ROOT
    assert a2 == ooupcast(ROOT, a)

def test_cast_object_record():
    R = Record({'x': Signed})
    r = new(R)
    r.x = 42
    obj = cast_to_object(r)
    assert typeOf(obj) is Object
    r2 = cast_from_object(R, obj)
    assert typeOf(r2) is R
    assert r == r2

def test_cast_object_null():
    A = Instance("Foo", ROOT)
    B = Record({'x': Signed})
    a = null(A)
    b = null(B)
    obj1 = cast_to_object(a)
    obj2 = cast_to_object(b)
    assert obj1 is obj2
    assert obj1 is NULL
    assert cast_from_object(A, obj1) == a
    assert cast_from_object(B, obj2) == b

def test_cast_object_compare_null():
    A = Instance("Foo", ROOT)
    a = new(A)
    obj1 = cast_to_object(a)
    assert NULL != obj1
    assert obj1 != NULL

def test_cast_object_class():
    A = Instance("Foo", ROOT)
    cls = runtimeClass(A)
    obj = cast_to_object(cls)
    cls2 = cast_from_object(Class, obj)
    assert cls is cls2
    
def test_object_identityhash():
    A = Instance("Foo", ROOT)
    a = new(A)
    obj1 = cast_to_object(a)
    obj2 = cast_to_object(a)
    assert identityhash(obj1) == identityhash(obj2)

def test_object_identityhash_sm():
    M = StaticMethod([Signed], Signed)
    def m_(x):
       return x
    m = static_meth(M, "m", _callable=m_)
    obj1 = cast_to_object(m)
    obj2 = cast_to_object(m)
    assert identityhash(obj1) == identityhash(obj2)

def test_identityhash_array():
    A = Array(Signed)
    a = oonewarray(A, 10)
    b = oonewarray(A, 10)
    assert identityhash(a) != identityhash(b)     # likely

def test_bool_class():
    A = Instance("Foo", ROOT)
    cls = runtimeClass(A)
    assert bool(cls)
    assert not bool(nullruntimeclass)

def test_bool_default_sm():
    SM = StaticMethod([], Void)
    sm = SM._defl()
    assert not bool(sm)

def test_get_fields_with_default():
    A = Instance("A", ROOT)
    addFields(A, {"a": (Signed, 3)}, with_default=True)
    addFields(A, {"b": (Signed, 0)}, with_default=True)
    addFields(A, {"c": (Signed, 0)}, with_default=False)
    fields = A._get_fields_with_default()
    assert fields == [("a", (Signed, 3)),
                      ("b", (Signed, 0))
                      ]

    B = Instance("B", A)
    addFields(B, {"d": (Signed, 4)}, with_default=True)
    fields = B._get_fields_with_default()
    assert fields == [("a", (Signed, 3)),
                      ("b", (Signed, 0)),
                      ("d", (Signed, 4)),
                      ]

