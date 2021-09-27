
class AppTestStackNew:
    def test_one(self):
        from _pypy_util import StackNew

        with StackNew("char[]", 1) as p:
            p[0] = b'\x13'
            assert p[0] == b'\x13'

        # assert did not crash
        with StackNew("char*") as p:
            pass
