import py
import locale
import sys

def setup_module(mod):
    if sys.platform == 'darwin':
        py.test.skip("Locale support on MacOSX is minimal and cannot be tested")

class TestLocale:
    def setup_class(cls):
        cls.oldlocale = locale.setlocale(locale.LC_NUMERIC)
        if sys.platform.startswith("win"):
            cls.tloc = "en"
        elif sys.platform.startswith("freebsd"):
            cls.tloc = "en_US.US-ASCII"
        else:
            cls.tloc = "en_US.UTF8"
        try:
            locale.setlocale(locale.LC_NUMERIC, cls.tloc)
        except locale.Error:
            py.test.skip("test locale %s not supported" % cls.tloc)
            
    def teardown_class(cls):
        locale.setlocale(locale.LC_NUMERIC, cls.oldlocale)

    def test_format(self):

        def testformat(formatstr, value, grouping = 0, output=None):
            if output:
                print "%s %% %s =? %s ..." %\
                      (repr(formatstr), repr(value), repr(output)),
            else:
                print "%s %% %s works? ..." % (repr(formatstr), repr(value)),
            result = locale.format(formatstr, value, grouping = grouping)
            assert result == output

        testformat("%f", 1024, grouping=1, output='1,024.000000')
        testformat("%f", 102, grouping=1, output='102.000000')
        testformat("%f", -42, grouping=1, output='-42.000000')
        testformat("%+f", -42, grouping=1, output='-42.000000')
        testformat("%20.f", -42, grouping=1, output='                 -42')
        testformat("%+10.f", -4200, grouping=1, output='    -4,200')
        testformat("%-10.f", 4200, grouping=1, output='4,200     ')
        # Invoke getpreferredencoding to make sure it does not cause exceptions,
        locale.getpreferredencoding()

    # Test BSD Rune locale's bug for isctype functions.
    def test_bsd_bug(self):
        def teststrop(s, method, output):
            print "%s.%s() =? %s ..." % (repr(s), method, repr(output)),
            result = getattr(s, method)()
            assert result == output

        oldlocale = locale.setlocale(locale.LC_CTYPE)
        locale.setlocale(locale.LC_CTYPE, self.tloc)
        try:
            teststrop('\x20', 'isspace', True)
            teststrop('\xa0', 'isspace', False)
            teststrop('\xa1', 'isspace', False)
            teststrop('\xc0', 'isalpha', False)
            teststrop('\xc0', 'isalnum', False)
            teststrop('\xc0', 'isupper', False)
            teststrop('\xc0', 'islower', False)
            teststrop('\xec\xa0\xbc', 'split', ['\xec\xa0\xbc'])
            teststrop('\xed\x95\xa0', 'strip', '\xed\x95\xa0')
            teststrop('\xcc\x85', 'lower', '\xcc\x85')
            teststrop('\xed\x95\xa0', 'upper', '\xed\x95\xa0')
        finally:
            locale.setlocale(locale.LC_CTYPE, oldlocale)
