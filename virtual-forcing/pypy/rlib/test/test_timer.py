from pypy.rlib.timer import Timer
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.policy import AnnotatorPolicy


t = Timer()
t.start("testc")
t.stop("testc")

def timer_user():
    assert "testc" not in t.timingorder
    t.start("testa")
    t.stop("testa")
    t.start("testb")
    t.start("testb")
    t.stop("testb")
    t.stop("testb")
    t.dump()


def test_compile_timer():
    policy = AnnotatorPolicy()
    policy.allow_someobjects = False
    f_compiled = compile(timer_user, [], annotatorpolicy=policy)
    f_compiled(expected_extra_mallocs=2)

