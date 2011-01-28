
import py
py.test.skip("DEMO")

class TestPyPyCNew(object):
    def test_one(self):
        def f():
            i = 0
            while i < 1003:
                # LOOP one
                i += 1

        trace = self.run(f, [])
        loop = trace.get_loops('one')
        loop.get_bytecode(3, 'LOAD_FAST').match('''
        int_add
        guard_true
        ''')
        loop.get_bytecode(4, 'LOAD_CONST').match_stats(
            guard='3', call='1-2', call_may_force='0'
        )
        # this would make operations that are "costly" obligatory to pass
        # like new
        loo.get_bytecode(5, 'INPLACE_ADD').match_stats(
            allocs='5-10'
            )
