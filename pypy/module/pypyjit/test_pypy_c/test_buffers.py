from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestBuffers(BaseTestPyPyC):
    def test_re_match(self):
        def main():
            import re
            import array
            p = re.compile('.+')
            a = array.array('c', 'test' * 1000)
            i = 0
            while i < 5000:
                i += 1
                p.match(a)  # ID: match
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('match', """
            guard_not_invalidated(descr=...)
            i65 = getfield_gc(p18, descr=...)
            i67 = int_gt(0, i65)
            guard_false(i67, descr=...)
            i69 = int_gt(., i65)
            guard_true(i69, descr=...)
            guard_not_invalidated(descr=...)
            i74 = getfield_raw(., descr=...)
            i75 = int_lt(i74, 0)
            guard_false(i75, descr=...)
        """)
