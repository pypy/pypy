import unittest
from distutils.msvccompiler import get_manifests

class MsvcCompilerTestCase(unittest.TestCase):
    def test_get_manifests(self):
        manifests = get_manifests()
        self.assert_(manifests)
        for manifest in manifests:
            if '"Microsoft.VC' in manifest:
                break
        else:
            self.fail("could not find a suitable manifest")

def test_suite():
    return unittest.makeSuite(MsvcCompilerTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
