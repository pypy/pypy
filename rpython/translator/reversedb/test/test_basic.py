import py
import os
import array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation


class RDB(object):
    def __init__(self, filename):
        f = open(filename, 'rb')
        f.seek(0, 2)
        filesize = f.tell()
        f.seek(0, 0)
        self.items = array.array("l")
        self.items.fromfile(f, filesize / struct.calcsize("l"))
        f.close()
        #
        assert self.items[0] == 0x0A424452
        assert self.items[1] == 0x00FF0001
        assert self.items[2] == 0
        assert self.items[3] == 0
        self.argc = self.items[4]
        self.argv = self.items[5]
        self.cur = 6

    def next(self):
        n = self.cur
        self.cur = n + 1
        return self.items[n]


class TestBasic(object):

    def getcompiled(self, entry_point, argtypes, backendopt=True):
        t = Translation(entry_point, None, gc="boehm")
        t.config.translation.reversedb = True
        t.config.translation.rweakref = False
        if not backendopt:
            t.disable(["backendopt_lltype"])
        t.annotate()
        t.rtype()
        if t.backendopt:
            t.backendopt()
        self.exename = t.compile_c()
        self.rdbname = os.path.join(os.path.dirname(str(self.exename)),
                                    'log.rdb')

        def run(*argv):
            env = os.environ.copy()
            env['PYPYRDB'] = self.rdbname
            stdout = t.driver.cbuilder.cmdexec(' '.join(argv), env=env)
            return stdout
        return run

    def fetch_rdb(self):
        return RDB(self.rdbname)

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 0
        fn = self.getcompiled(main, [], backendopt=False)
        assert fn('abc d') == '[abc, d]\n'
        rdb = self.fetch_rdb()
        assert rdb.argc == 3
        #
        got = []
        for i in range(3):
            rdb.next()    # ignore the address of argv[i]
            s = []
            while True:
                c = rdb.next()
                if c == 0:
                    break
                s.append(chr(c))
            for c1 in s:
                c2 = rdb.next()
                assert c2 == ord(c1)
            got.append(''.join(s))
        assert rdb.cur == len(rdb.items)
        #
        assert got == [self.exename, 'abc', 'd']
