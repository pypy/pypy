
""" Tests some error handling routines
"""

from pypy.translator.translator import TranslationContext
from pypy.tool.error import FlowingError, AnnotatorError, NoSuchAttrError
from pypy.annotation.policy import BasicAnnotatorPolicy

import py

class Policy(BasicAnnotatorPolicy):
    allow_someobjects = False

def compile_function(function, annotation=[]):
    t = TranslationContext()
    t.buildannotator(policy=Policy()).build_types(function, annotation)

def test_global_variable():
    def global_var_missing():
        return a
    
    rex = py.test.raises(FlowingError, compile_function, global_var_missing)
    assert str(rex.exconly()).find("global variable 'a' undeclared")

class AAA(object):
    pass

def test_blocked_inference1():
    def blocked_inference():
        return AAA().m()
    
    py.test.raises(AnnotatorError, compile_function, blocked_inference)

def test_blocked_inference2():
    def blocked_inference():
        a = AAA()
        b = a.x
        return b
    
    py.test.raises(AnnotatorError, compile_function, blocked_inference)

def test_someobject():
    def someobject_degeneration(n):
        if n == 3:
            a = "a"
        else:
            a = 9
        return a

    py.test.raises(AnnotatorError, compile_function, someobject_degeneration, [int])

def test_someobject2():
    def someobject_deg(n):
        if n == 3:
            a = "a"
        else:
            return AAA()
        return a

    py.test.raises(AnnotatorError, compile_function, someobject_deg, [int])

def test_eval():
    exec("def f(): return a")
    
    py.test.raises(FlowingError, compile_function, f)

def test_eval_someobject():
    exec("def f(n):\n if n == 2:\n  return 'a'\n else:\n  return 3")
    
    py.test.raises(AnnotatorError, compile_function, f, [int])

def test_someobject_from_call():
    def one(x):
        return str(x)

    def two(x):
        return int(x)

    def fn(n):
        if n:
            to_call = one
        else:
            to_call = two
        return to_call(n)

    try:
        compile_function(fn, [int])
    except AnnotatorError, e:
        assert 'function one' in e.args[0]
        assert 'function two' in e.args[0]
