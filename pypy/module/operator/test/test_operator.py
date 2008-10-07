
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

