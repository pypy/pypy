import py
from pypy.module.pypyjit.test_pypy_c.test_model import BaseTestPyPyC

class Test__ffi(BaseTestPyPyC):

    def test__ffi_call(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            try:
                from _ffi import CDLL, types
            except ImportError:
                sys.stderr.write('SKIP: cannot import _ffi\n')
                return 0

            libm = CDLL(libm_name)
            pow = libm.getfunc('pow', [types.double, types.double],
                               types.double)
            i = 0
            res = 0
            while i < 300:
                tmp = pow(2, 3)   # ID: fficall
                res += tmp
                i += 1
            return pow.getaddr(), res
        #
        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        pow_addr, res = log.result
        assert res == 8.0 * 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('fficall', """
            p16 = getfield_gc(ConstPtr(ptr15), descr=<.* .*Function.inst_name .*>)
            guard_not_invalidated(descr=...)
            i17 = force_token()
            setfield_gc(p0, i17, descr=<.* .*PyFrame.vable_token .*>)
            f21 = call_release_gil(%d, 2.000000, 3.000000, descr=<FloatCallDescr>)
            guard_not_forced(descr=...)
            guard_no_exception(descr=...)
        """ % pow_addr)


    def test__ffi_call_frame_does_not_escape(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            try:
                from _ffi import CDLL, types
            except ImportError:
                sys.stderr.write('SKIP: cannot import _ffi\n')
                return 0

            libm = CDLL(libm_name)
            pow = libm.getfunc('pow', [types.double, types.double],
                               types.double)

            def mypow(a, b):
                return pow(a, b)

            i = 0
            res = 0
            while i < 300:
                tmp = mypow(2, 3)
                res += tmp
                i += 1
            return pow.getaddr(), res
        #
        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        pow_addr, res = log.result
        assert res == 8.0 * 300
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        # we only force the virtualref, not its content
        assert opnames.count('new_with_vtable') == 1

    def test__ffi_call_releases_gil(self):
        from pypy.rlib.test.test_libffi import get_libc_name
        def main(libc_name, n):
            import time
            from threading import Thread
            from _ffi import CDLL, types
            #
            libc = CDLL(libc_name)
            sleep = libc.getfunc('sleep', [types.uint], types.uint)
            delays = [0]*n + [1]
            #
            def loop_of_sleeps(i, delays):
                for delay in delays:
                    sleep(delay)    # ID: sleep
            #
            threads = [Thread(target=loop_of_sleeps, args=[i, delays]) for i in range(5)]
            start = time.time()
            for i, thread in enumerate(threads):
                thread.start()
            for thread in threads:
                thread.join()
            end = time.time()
            return end - start
        #
        log = self.run(main, [get_libc_name(), 200], threshold=150)
        assert 1 <= log.result <= 1.5 # at most 0.5 seconds of overhead
        loops = log.loops_by_id('sleep')
        assert len(loops) == 1 # make sure that we actually JITted the loop


    def test_ctypes_call(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            import ctypes
            libm = ctypes.CDLL(libm_name)
            fabs = libm.fabs
            fabs.argtypes = [ctypes.c_double]
            fabs.restype = ctypes.c_double
            x = -4
            i = 0
            while i < 300:
                x = fabs(x)
                x = x - 100
                i += 1
            return fabs._ptr.getaddr(), x

        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        fabs_addr, res = log.result
        assert res == -4.0
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.allops()
        opnames = log.opnames(ops)
        assert opnames.count('new_with_vtable') == 1 # only the virtualref
        assert opnames.count('call_release_gil') == 1
        idx = opnames.index('call_release_gil')
        call = ops[idx]
        assert int(call.args[0]) == fabs_addr
