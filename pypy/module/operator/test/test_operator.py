
class AppTestOperator:
    def test_equality(self):
        import operator
        assert operator.eq == operator.__eq__

    def test_getters_are_not_regular_functions(self):
        import operator
        class A(object):
            getx = operator.attrgetter('x')
            get3 = operator.itemgetter(3)
        a = A()
        a.x = 5
        assert a.getx(a) == 5
        assert a.get3("foobar") == "b"
        assert a.getx(*(a,)) == 5
        assert a.get3(obj="foobar") == "b"
        

    def test_getter_multiple_gest(self):
        import operator

        class A(object):
            pass

        a = A()
        a.x = 'X'
        a.y = 'Y'
        a.z = 'Z'

        assert operator.attrgetter('x','z','y')(a) == ('X', 'Z', 'Y')
        raises(TypeError, operator.attrgetter('x', (), 'y'), a)

        data = map(str, range(20))
        assert operator.itemgetter(2,10,5)(data) == ('2', '10', '5')
        raises(TypeError, operator.itemgetter(2, 'x', 5), data)

    def test_concat(self):
        class Seq1:
            def __init__(self, lst):
                self.lst = lst
            def __len__(self):
                return len(self.lst)
            def __getitem__(self, i):
                return self.lst[i]
            def __add__(self, other):
                return self.lst + other.lst
            def __mul__(self, other):
                return self.lst * other
            def __rmul__(self, other):
                return other * self.lst

        class Seq2(object):
            def __init__(self, lst):
                self.lst = lst
            def __len__(self):
                return len(self.lst)
            def __getitem__(self, i):
                return self.lst[i]
            def __add__(self, other):
                return self.lst + other.lst
            def __mul__(self, other):
                return self.lst * other
            def __rmul__(self, other):
                return other * self.lst

        import operator

        raises(TypeError, operator.concat)
        raises(TypeError, operator.concat, None, None)
        assert operator.concat('py', 'thon') == 'python'
        assert operator.concat([1, 2], [3, 4]) == [1, 2, 3, 4]
        assert operator.concat(Seq1([5, 6]), Seq1([7])) == [5, 6, 7]
        assert operator.concat(Seq2([5, 6]), Seq2([7])) == [5, 6, 7]
        raises(TypeError, operator.concat, 13, 29)

    def test_repeat(self):
        class Seq1:
            def __init__(self, lst):
                self.lst = lst
            def __len__(self):
                return len(self.lst)
            def __getitem__(self, i):
                return self.lst[i]
            def __add__(self, other):
                return self.lst + other.lst
            def __mul__(self, other):
                return self.lst * other
            def __rmul__(self, other):
                return other * self.lst

        class Seq2(object):
            def __init__(self, lst):
                self.lst = lst
            def __len__(self):
                return len(self.lst)
            def __getitem__(self, i):
                return self.lst[i]
            def __add__(self, other):
                return self.lst + other.lst
            def __mul__(self, other):
                return self.lst * other
            def __rmul__(self, other):
                return other * self.lst

        import operator

        a = range(3)
        raises(TypeError, operator.repeat)
        raises(TypeError, operator.repeat, a, None)
        assert operator.repeat(a, 2) == a+a
        assert operator.repeat(a, 1) == a
        assert operator.repeat(a, 0) == []
        a = (1, 2, 3)
        assert operator.repeat(a, 2) == a+a
        assert operator.repeat(a, 1) == a
        assert operator.repeat(a, 0) == ()
        a = '123'
        assert operator.repeat(a, 2) == a+a
        assert operator.repeat(a, 1) == a
        assert operator.repeat(a, 0) == ''
        a = Seq1([4, 5, 6])
        assert operator.repeat(a, 2) == [4, 5, 6, 4, 5, 6]
        assert operator.repeat(a, 1) == [4, 5, 6]
        assert operator.repeat(a, 0) == []
        a = Seq2([4, 5, 6])
        assert operator.repeat(a, 2) == [4, 5, 6, 4, 5, 6]
        assert operator.repeat(a, 1) == [4, 5, 6]
        assert operator.repeat(a, 0) == []
        raises(TypeError, operator.repeat, 6, 7)

    def test_isSequenceType(self):
        import operator

        raises(TypeError, operator.isSequenceType)
        assert operator.isSequenceType(dir())
        assert operator.isSequenceType(())
        assert operator.isSequenceType(xrange(10))
        assert operator.isSequenceType('yeahbuddy')
        assert not operator.isSequenceType(3)
        class Dict(dict): pass
        assert not operator.isSequenceType(Dict())

    def test_inplace(self):
        import operator

        list = []
        assert operator.iadd(list, [1, 2]) is list
        assert list == [1, 2]

        list = [1, 2]
        assert operator.imul(list, 2) is list
        assert list == [1, 2, 1, 2]

    def test_irepeat(self):
        import operator
        import py

        class X(object):
            def __index__(self):
                return 5

        a = range(3)
        raises(TypeError, operator.irepeat)
        raises(TypeError, operator.irepeat, a, None)
        raises(TypeError, operator.irepeat, a, [])
        raises(TypeError, operator.irepeat, a, X())
        raises(TypeError, operator.irepeat, 6, 7)
        assert operator.irepeat(a, 2L) is a
        assert a == [0, 1, 2, 0, 1, 2]
        assert operator.irepeat(a, 1) is a
        assert a == [0, 1, 2, 0, 1, 2]

