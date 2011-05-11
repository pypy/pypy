from pypy.module._multibytecodec import c_codecs
from pypy.translator.c.test import test_standalone


class TestTranslation(test_standalone.StandaloneTests):

    def test_translation(self):
        #
        def entry_point(argv):
            codecname, string = argv[1], argv[2]
            c = c_codecs.getcodec(codecname)
            u = c_codecs.decode(c, string)
            r = c_codecs.encode(c, u)
            print r
            return 0
        #
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hz \~\{abc\}')
        assert data == '~{abc}~}\n'
