
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
