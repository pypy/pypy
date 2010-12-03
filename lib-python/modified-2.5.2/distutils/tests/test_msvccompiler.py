import unittest, sys

class MsvcCompilerTestCase(unittest.TestCase):
    def test_get_manifests(self):
        from distutils.msvccompiler import get_manifests
        manifests = get_manifests()
        self.assert_(manifests)
        for manifest in manifests:
            if '"Microsoft.VC' in manifest:
                break
        else:
            self.fail("could not find a suitable manifest")

class MsvcCompilerSimplerTestCase(unittest.TestCase):
    def test_import_module(self):
        from distutils.msvccompiler import MSVCCompiler

def test_suite():
    if sys.platform == 'win32':
        return unittest.makeSuite(MsvcCompilerTestCase)
    else:
        return unittest.makeSuite(MsvcCompilerSimplerTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
