
from pypy.translator.platform.test.test_platform import TestPlatform as BasicTest
from pypy.translator.platform.distutils_platform import DistutilsPlatform
import py

class TestDistutils(BasicTest):
    platform = DistutilsPlatform()

    def test_nice_errors(self):
        py.test.skip("Unsupported")
