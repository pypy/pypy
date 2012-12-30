from rpython.rlib.timer import Timer
from rpython.translator.c.test.test_genc import compile
from rpython.annotator.policy import AnnotatorPolicy


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
    t.start_name("test", "one")
    t.stop_name("test", "one")
    t.dump()


def test_compile_timer():
    policy = AnnotatorPolicy()
    f_compiled = compile(timer_user, [], annotatorpolicy=policy)
    f_compiled()
