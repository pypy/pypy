"""Tests for distutils._msvccompiler."""
import sys
import unittest
import os
import threading

from distutils.errors import DistutilsPlatformError
from distutils.tests import support
from test.support import run_unittest


SKIP_MESSAGE = (None if sys.platform == "win32" else
                "These tests are only for win32")

@unittest.skipUnless(SKIP_MESSAGE is None, SKIP_MESSAGE)
class msvccompilerTestCase(support.TempdirManager,
                            unittest.TestCase):

    def test_no_compiler(self):
        import distutils._msvccompiler as _msvccompiler
        # makes sure query_vcvarsall raises
        # a DistutilsPlatformError if the compiler
        # is not found
        def _find_vcvarsall(plat_spec):
            return None, None

        old_find_vcvarsall = _msvccompiler._find_vcvarsall
        _msvccompiler._find_vcvarsall = _find_vcvarsall
        try:
            self.assertRaises(DistutilsPlatformError,
                              _msvccompiler._get_vc_env,
                             'wont find this version')
        finally:
            _msvccompiler._find_vcvarsall = old_find_vcvarsall

    def test_get_vc_env_unicode(self):
        import distutils._msvccompiler as _msvccompiler

        test_var = 'ṰḖṤṪ┅ṼẨṜ'
        test_value = '₃⁴₅'

        # Ensure we don't early exit from _get_vc_env
        old_distutils_use_sdk = os.environ.pop('DISTUTILS_USE_SDK', None)
        os.environ[test_var] = test_value
        try:
            env = _msvccompiler._get_vc_env('x86')
            self.assertIn(test_var.lower(), env)
            self.assertEqual(test_value, env[test_var.lower()])
        finally:
            os.environ.pop(test_var)
            if old_distutils_use_sdk:
                os.environ['DISTUTILS_USE_SDK'] = old_distutils_use_sdk

    def test_get_vc2017(self):
        import distutils._msvccompiler as _msvccompiler

        # This function cannot be mocked, so pass it if we find VS 2017
        # and mark it skipped if we do not.
        version, path = _msvccompiler._find_vc2017()
        if version:
            self.assertGreaterEqual(version, 15)
            self.assertTrue(os.path.isdir(path))
        else:
            raise unittest.SkipTest("VS 2017 is not installed")

    def test_get_vc2015(self):
        import distutils._msvccompiler as _msvccompiler

        # This function cannot be mocked, so pass it if we find VS 2015
        # and mark it skipped if we do not.
        version, path = _msvccompiler._find_vc2015()
        if version:
            self.assertGreaterEqual(version, 14)
            self.assertTrue(os.path.isdir(path))
        else:
            raise unittest.SkipTest("VS 2015 is not installed")


class CheckThread(threading.Thread):
    exc_info = None

    def run(self):
        try:
            super().run()
        except Exception:
            self.exc_info = sys.exc_info()

    def __bool__(self):
        return not self.exc_info


class TestSpawn(unittest.TestCase):
    def test_concurrent_safe(self):
        """
        Concurrent calls to spawn should have consistent results.
        """
        import distutils._msvccompiler as _msvccompiler
        compiler = _msvccompiler.MSVCCompiler()
        compiler._paths = "expected"
        inner_cmd = 'import os; assert os.environ["PATH"] == "expected"'
        command = ['python', '-c', inner_cmd]

        threads = [
            CheckThread(target=compiler.spawn, args=[command])
            for n in range(100)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert all(threads)

    def test_concurrent_safe_fallback(self):
        """
        If CCompiler.spawn has been monkey-patched without support
        for an env, it should still execute.
        """
        import distutils._msvccompiler as _msvccompiler
        from distutils import ccompiler
        compiler = _msvccompiler.MSVCCompiler()
        compiler._paths = "expected"

        def CCompiler_spawn(self, cmd):
            "A spawn without an env argument."
            assert os.environ["PATH"] == "expected"

        with unittest.mock.patch.object(
                ccompiler.CCompiler, 'spawn', CCompiler_spawn):
            compiler.spawn(["n/a"])

        assert os.environ.get("PATH") != "expected"


def test_suite():
    return unittest.makeSuite(msvccompilerTestCase)

if __name__ == "__main__":
    run_unittest(test_suite())
