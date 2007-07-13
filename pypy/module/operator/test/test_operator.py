
class AppTestOperator:
    def test_equality(self):
        import operator
        assert operator.eq == operator.__eq__
