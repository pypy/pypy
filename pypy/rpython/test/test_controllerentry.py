from pypy.rpython.controllerentry import Controller, ControllerEntry

from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret


class C:
    "Imagine some magic here to have a foo attribute on instances"

def fun(a):
    lst = []
    c = C(a)
    c.foo = lst    # side-effect on lst!  well, it's a test
    return c.foo, lst[0]

class C_Controller(Controller):
    knowntype = C

    def new(self, a):
        return a + '_'

    def get_foo(self, obj):
        return obj + "2"

    def set_foo(self, obj, value):
        value.append(obj)

class Entry(ControllerEntry):
    _about_ = C
    _controller_ = C_Controller


def test_C_annotate():
    a = RPythonAnnotator()
    s = a.build_types(fun, [a.bookkeeper.immutablevalue("4")])
    assert s.const == ("4_2", "4_")

def test_C_specialize():
    res = interpret(fun, ["4"])
    assert ''.join(res.item0.chars) == "4_2"
    assert ''.join(res.item1.chars) == "4_"
