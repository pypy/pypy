from pypy.rpython.ootypesystem import ootype

# used in tests below
class A:
    pass

class BaseTestConstant:
    def test_char(self):
        const = 'a'
        def fn():
            return const
        assert self.interpret(fn, []) == 'a'

    def test_void(self):
        def fn():
            pass
        assert self.interpret(fn, []) is None
        
    def test_tuple(self):
        const = 1, 2
        def fn():
            return const
        res = self.interpret(fn, [])
        assert res.item0 == 1
        assert res.item1 == 2

    def test_tuples_of_different_types(self):
        const = "1", "2"
        def fn():
            return const
        res = self.interpret(fn, [])
        assert res.item0 == "1"
        assert res.item1 == "2"

    def test_list(self):
        const = [1, 2]
        def fn():
            return const
        res = self.ll_to_list(self.interpret(fn, []))
        assert res == [1, 2]

    def test_compound_const(self):
        const = ([1, 2], [3, 4])
        def fn():
            return const
        res = self.interpret(fn, [])
        assert self.ll_to_list(res.item0) == [1, 2]
        assert self.ll_to_list(res.item1) == [3, 4]
        
    def test_instance(self):
        const = A()
        def fn():
            return const
        res = self.interpret(fn, [])
        assert self.class_name(res) == 'A'

    def test_list_of_zeroes(self):
        const = [0] * 10
        def fn():
            return const
        res = self.ll_to_list(self.interpret(fn, []))
        assert res == const

    def test_list_of_instances(self):
        const = [A()]
        def fn():
            return const
        res = self.ll_to_list(self.interpret(fn, []))
        assert self.class_name(res[0]) == 'A'

    def test_mix_string_and_char(self):
        def fn(x):
            if x < 0:
                return 'a'
            else:
                return 'aa'
        assert self.ll_to_string(self.interpret(fn, [-1])) == 'a'
        assert self.ll_to_string(self.interpret(fn, [0])) == 'aa'

    def test_string_literal(self):
        def fn():
            return 'hello "world"'
        assert self.ll_to_string(self.interpret(fn, [])) == 'hello "world"'

    def test_string_literal2(self):
        literals = ['\001\002\003', '\004\005\006']
        def fn(i):
            s = literals[i]
            return len(s), ord(s[0]) + ord(s[1]) + ord(s[2])
        res = self.interpret(fn, [0])
        assert res.item0 == 3
        assert res.item1 == 6
        res = self.interpret(fn, [1])
        assert res.item0 == 3
        assert res.item1 == 15

    def test_float_special(self):
        self._skip_win('inf & nan')
        self._skip_powerpc('Suspected endian issue with '+
                           'representation of INF and NAN')
        c = [float("inf"), float("nan")]
        def fn(i):
            return c[i]*2 == c[i]
        def fn2(i):
            return c[i] != c[i]
        assert self.interpret(fn, [0]) == True
        assert self.interpret(fn2, [1]) == True

    def test_customdict_circular(self):
        from pypy.rlib.objectmodel import r_dict
        def key_eq(a, b):
            return a.x[0] == b.x[0]
        def key_hash(a):
            return ord(a.x[0])

        class A:
            def __init__(self, x):
                self.x = x
        a = A('foo')
        a.dict = r_dict(key_eq, key_hash)
        a.dict[a] = 42
        def fn(b):
            if b:
                s = A('foo')
            else:
                s = A('bar')
            return a.dict[s]
        assert self.interpret(fn, [True]) == 42

    def test_multiple_step(self):
        from pypy.translator.oosupport import constant
        constant.MAX_CONST_PER_STEP = 2
        c1 = [1]
        c2 = [2]
        def fn(x, y):
            return c1[x] + c2[y]
        assert self.interpret(fn, [0, 0]) == 3

    def test_many_constants(self):
        N = 7500
        class A:
            pass
        mylist = [A() for i in range(N)]
        def fn(x):
            return mylist[x]
        res = self.interpret(fn, [0])
        assert self.class_name(res) == 'A'

    def test_convert_string_to_object(self):
        s = self.string_to_ll("hello world")
        obj = ootype.cast_to_object(s)
        def fn():
            s1 = ootype.cast_from_object(ootype.String, obj)
            return s1
        res = self.interpret(fn, [], backendopt=False)
        assert res == 'hello world'

    def test_unwrap_object(self):
        A = ootype.Instance("A", ootype.ROOT, {})
        a1 = ootype.new(A)
        a2 = ootype.new(A)
        obj1 = ootype.cast_to_object(a1)
        obj2 = ootype.cast_to_object(a2)
        def fn(flag):
            if flag:
                obj = obj1
            else:
                obj = obj2
            a3 = ootype.cast_from_object(A, obj)
            return a3 is a1
        res = self.interpret(fn, [True], backendopt=False)
        assert res is True
    
