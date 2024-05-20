from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestCaptureLocals(BaseTestPyPyC):
    def test_capture_locals(self):
        def main(n):
            num = 42
            i = 0
            acc = 0
            src = '''
while i < n:
    acc += num
    i += 1
'''
            exec(src)
            return acc

        log = self.run(main, [500])
        print (log.result)
        assert log.result == 0
        loop, = log.loops_by_filename("<string>")
        assert loop.match("""
            guard_not_invalidated(descr=...)
            i48 = int_lt(i41, i33)
            guard_true(i48, descr=...)
            i49 = int_add_ovf(i39, i38)
            guard_no_overflow(descr=...)
            i51 = int_add(i41, 1)
            i53 = getfield_raw_i(..., descr=...)
            setarrayitem_gc(p27, 3, i49, descr=...)
            setarrayitem_gc(p27, 2, i51, descr=...)
            i57 = int_lt(i53, 0)
            guard_false(i57, descr=...)
            i59 = arraylen_gc(p25, descr=...)
            i60 = arraylen_gc(p27, descr=...)
            jump(..., descr=...)
        """)
