import pytest
from rpython.tool.udir import udir


def test_recursion_error_in_subprocess(space):
    import py
    import sys
    if sys.platform == "win32":
        pytest.skip("no ForkedProcess on windows")

    def f():
        space.appexec([], """():
        # test from CPython

        import marshal
        def run_tests(N, check):
            # (((...None...),),)
            check(b')\x01' * N + b'N')
            # PyPy fix: use bytes(3) instead of literal null bytes to avoid
            # null bytes in the source string passed to the compiler
            check((b'(\x01' + bytes(3)) * N + b'N')
            # [[[...None...]]]
            check((b'[\x01' + bytes(3)) * N + b'N')
            # {None: {None: {None: ...None...}}}
            check(b'{N' * N + b'N' + b'0' * N)
            # frozenset([frozenset([frozenset([...None...])])])
            check((b'>\x01' + bytes(3)) * N + b'N')
        # Check that the generated marshal data is valid and marshal.loads()
        # works for moderately deep nesting
        run_tests(100, marshal.loads)
        # Very deeply nested structure shouldn't blow the stack
        def check(s):
            raises(ValueError, marshal.loads, s)
        run_tests(2**20, check)""")

    ff = py.process.ForkedFunc(f)
    res = ff.waitfinish()
    assert res.exitstatus == 0, res.err
