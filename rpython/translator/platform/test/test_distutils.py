
from rpython.translator.platform.test.test_platform import TestPlatform as BasicTest
from rpython.translator.platform.distutils_platform import DistutilsPlatform
import py

class TestDistutils(BasicTest):
    platform = DistutilsPlatform()

    def test_nice_errors(self):
        py.test.skip("Unsupported")

    def test_900_files(self):
        py.test.skip('Makefiles not suppoerted')

    def test_precompiled_headers(self):
        py.test.skip('Makefiles not suppoerted')

