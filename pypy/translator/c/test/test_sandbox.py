import sys, os
import struct

from pypy.rpython.lltypesystem import rffi
from pypy.translator.c.sandboxmsg import Message, MessageBuilder, read_message
from pypy.translator.interactive import Translation


def test_sandbox_message():
    def num(n):
        return struct.pack("!i", n)
    msg = MessageBuilder()
    msg.packstring("open")
    msg.packccharp(rffi.str2charp("/tmp/foobar"))
    msg.packnum(123)
    res = msg.getvalue()
    assert res == (num(len(res)) +
                   "s" + num(4) + "open" +
                   "s" + num(11) + "/tmp/foobar" +
                   "i" + num(123))

    msg = Message(res[4:])
    m1 = msg.nextstring()
    assert m1 == "open"
    m2 = msg.nextstring()
    assert m2 == "/tmp/foobar"
    m3 = msg.nextnum()
    assert m3 == 123

def test_sandbox():
    def entry_point(argv):
        fd = os.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        fd2 = os.dup(fd)
        assert fd2 == 78
        return 0

    t = Translation(entry_point, backend='c', standalone=True, sandbox=True)
    exe = t.compile()
    g, f = os.popen2(exe, "t", 0)

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "open"
    m2 = msg.nextstring()
    assert m2 == "/tmp/foobar"
    m3 = msg.nextnum()
    assert m3 == os.O_RDONLY
    m4 = msg.nextnum()
    assert m4 == 0777
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packnum(77).getvalue())

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "dup"
    m2 = msg.nextnum()
    assert m2 == 77
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packnum(78).getvalue())

    g.close()
    tail = f.read()
    f.close()
    assert tail == ""

def test_sandbox_2():
    def entry_point(argv):
        fd = os.open("/tmp/foobar", os.O_RDONLY, 0777)
        assert fd == 77
        res = os.read(fd, 123)
        assert res == "he\x00llo"
        count = os.write(fd, "world\x00!\x00")
        assert count == 42
        os.close(fd)
        return 0

    t = Translation(entry_point, backend='c', standalone=True, sandbox=True)
    exe = t.compile()
    g, f = os.popen2(exe, "t", 0)

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "open"
    m2 = msg.nextstring()
    assert m2 == "/tmp/foobar"
    m3 = msg.nextnum()
    assert m3 == os.O_RDONLY
    m4 = msg.nextnum()
    assert m4 == 0777
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packnum(77).getvalue())

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "read"
    m2 = msg.nextnum()
    assert m2 == 77
    m3 = msg.nextsize_t()
    assert m3 == 123
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packstring("he\x00llo").getvalue())

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "write"
    m2 = msg.nextnum()
    assert m2 == 77
    m3 = msg.nextstring()
    assert m3 == "world\x00!\x00"
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packsize_t(42).getvalue())

    msg = read_message(f, timeout=10.0)
    m1 = msg.nextstring()
    assert m1 == "close"
    m2 = msg.nextnum()
    assert m2 == 77
    assert msg.end()

    g.write(MessageBuilder().packnum(0).packnum(0).getvalue())

    g.close()
    tail = f.read()
    f.close()
    assert tail == ""
