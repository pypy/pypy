class TestOptimizeO:
    """Test interaction of -O flag and optimize parameter of compile."""

    def setup_method(self, method):
        space = self.space
        self._sys_debug = space.sys.debug
        # imitate -O
        space.sys.debug = False

    def teardown_method(self, method):
        self.space.sys.debug = self._sys_debug

    def test_O_optmize_0(self):
        """Test that assert is not ignored if -O flag is set but optimize=0."""
        space = self.space
        w_res = space.appexec([], """():
            assert False  # check that our -O imitation hack works
            try:
                exec(compile('assert False', '', 'exec', optimize=0))
            except AssertionError:
                return True
            else:
                return False
        """)
        assert space.unwrap(w_res)

    def test_O_optimize__1(self):
        """Test that assert is ignored with -O and optimize=-1."""
        space = self.space
        space.appexec([], """():
            exec(compile('assert False', '', 'exec', optimize=-1))
        """)


# TODO: Check the value of __debug__ inside of the compiled block!
#       According to the documentation, it should follow the optimize flag.
#       However, cpython3.5.0a0 behaves the same way as PyPy (__debug__ follows
#       -O, -OO flags of the interpreter).
