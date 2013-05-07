import sys

class BaseImportTest:

    def setup_class(cls):
        space = cls.space
        testfn = u'test_tmp'
        testfn_unencodable = None

        if sys.platform == 'win32':
            testfn_unencodable = testfn + u"-\u5171\u0141\u2661\u0363\uDC80"
        elif sys.platform != 'darwin':
            try:
                '\xff'.decode(sys.getfilesystemencoding())
            except UnicodeDecodeError:
                testfn_unencodable = testfn + u'-\udcff'
        cls.w_testfn_unencodable = space.wrap(testfn_unencodable)
