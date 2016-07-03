import os, subprocess
from rpython.rlib import revdb
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.revdb.test.test_basic import InteractiveTests

from rpython.translator.revdb.message import *


class TestReplayingRaw(InteractiveTests):
    expected_stop_points = 1

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run
        from rpython.translator.revdb.test.test_basic import fetch_rdb

        FOO = lltype.Struct('FOO')
        foo = lltype.malloc(FOO, flavor='raw', immortal=True)

        BAR = lltype.Struct('BAR', ('p', lltype.Ptr(FOO)))
        bar = lltype.malloc(BAR, flavor='raw', immortal=True)
        bar.p = foo

        BAZ = lltype.Struct('BAZ', ('p', lltype.Ptr(FOO)), ('q', lltype.Signed),
                            hints={'union': True})
        baz = lltype.malloc(BAZ, flavor='raw', immortal=True)
        baz.p = foo

        VBAR = lltype.Array(lltype.Ptr(FOO))
        vbar = lltype.malloc(VBAR, 3, flavor='raw', immortal=True)
        vbar[0] = vbar[1] = vbar[2] = foo

        def main(argv):
            assert bar.p == foo
            assert baz.p == foo
            for i in range(3):
                assert vbar[i] == foo
            revdb.stop_point()
            return 9

        compile(cls, main, backendopt=False)
        run(cls, '')
        rdb = fetch_rdb(cls, [cls.exename])
        assert len(rdb.rdb_struct) >= 4

    def test_replaying_raw(self):
        # This tiny test seems to always have foo at the same address
        # in multiple runs.  Here we recompile with different options
        # just to change that address.
        subprocess.check_call(["make", "clean"],
                              cwd=os.path.dirname(str(self.exename)))
        subprocess.check_call(["make", "lldebug"],
                              cwd=os.path.dirname(str(self.exename)))
        #
        child = self.replay()
        child.send(Message(CMD_FORWARD, 2))
        child.expect(ANSWER_AT_END)
