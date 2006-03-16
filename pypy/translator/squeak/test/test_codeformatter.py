from pypy.objspace.flow.model import Constant
from pypy.rpython.ootypesystem.ootype import Signed, Bool, Void
from pypy.translator.squeak.codeformatter import CodeFormatter
from pypy.translator.squeak.codeformatter import Message

C = Constant

def test_messagewithargs():
    c = CodeFormatter()
    m = Message("bla")
    assert c.format(m.with_args([])) == "bla"
    assert c.format(m.with_args([C(1, Signed), C(2, Signed)])) \
            == "bla: 1 with: 2"
    m = Message("+")
    assert c.format(m.with_args([C(1, Signed)])) == "+ 1"

def test_sentmessage():
    c = CodeFormatter()
    receiver = C(100, Signed)
    args = [C(1, Signed), C(2, Signed)]
    m = Message("bla").send_to(receiver, args)
    assert c.format(m) == "(100 bla: 1 with: 2)"
    m = Message("bla").with_args(args).send_to(receiver)
    assert c.format(m) == "(100 bla: 1 with: 2)"

def test_assignment():
    c = CodeFormatter()
    result = C(200, Signed)
    receiver = C(100, Signed)
    args = [C(1, Signed), C(2, Signed)]
    m = Message("bla").send_to(receiver, args).assign_to(result)
    assert c.format(m) == "200 := (100 bla: 1 with: 2)"

def test_argformatting():
    c = CodeFormatter()
    m = Message("b")
    bools = [C(True, Bool), C(False, Bool)]
    null = C(None, Void)
    assert c.format(m.with_args(bools)) == "b: true with: false"
    assert c.format(m.with_args([null])) == "b: nil"

