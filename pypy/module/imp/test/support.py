import sys

class BaseImportTest:

    def setup_class(cls):
        space = cls.space
        testfn = u'test_tmp'
        testfn_unencodable = None

        if sys.platform == 'nt':
            testfn_unencodable = testfn + u"-\u5171\u0141\u2661\u0363\uDC80"
        elif sys.platform != 'darwin':
            fsenc = sys.getfilesystemencoding()
            try:
                '\xff'.decode(fsenc)
            except UnicodeDecodeError:
                w_unenc = space.call_method(space.wrapbytes('-\xff'), 'decode',
                                            space.wrap(fsenc),
                                            space.wrap('surrogateescape'))
                testfn_unencodable = testfn + space.unicode_w(w_unenc)
        cls.w_testfn_unencodable = space.wrap(testfn_unencodable)
