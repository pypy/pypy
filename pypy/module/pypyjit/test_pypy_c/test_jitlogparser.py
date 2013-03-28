from rpython.tool.logparser import extract_category

from pypy.tool.jitlogparser.parser import import_log, parse_log_counts
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestLogParser(BaseTestPyPyC):

    def test(self):
        def fn_with_bridges(N):
            def is_prime(x):
                for y in xrange(2, x):
                    if x % y == 0:
                        return False
                return True
            result = 0
            for x in xrange(N):
                if x % 3 == 0:
                    result += 5
                elif x % 5 == 0:
                    result += 3
                elif is_prime(x):
                    result += x
                elif x == 99:
                    result *= 2
            return result
        #
        log = self.run(fn_with_bridges, [10000])
        print log
        import pdb; pdb.set_trace()
        # TODO
        log, loops = import_log(log_filename)
        parse_log_counts(extract_category(log, 'jit-backend-count'), loops)
        lib_re = re.compile("file '.*lib-python.*'")
        for loop in loops:
            loop.force_asm()
            if lib_re.search(loop.comment) or \
                    lib_re.search(loop.operations[0].repr()):
                # do not care for _optimize_charset or _mk_bitmap
                continue
            else:
                import pdb; pdb.set_trace()


