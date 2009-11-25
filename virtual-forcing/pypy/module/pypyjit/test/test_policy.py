from pypy.module.pypyjit import policy

pypypolicy = policy.PyPyJitPolicy()

def test_id_any():
    from pypy.objspace.std.default import id__ANY
    assert not pypypolicy.look_inside_function(id__ANY)

def test_bigint():
    from pypy.rlib.rbigint import rbigint
    assert not pypypolicy.look_inside_function(rbigint.lt.im_func)

def test_geninterp():
    d = {'_geninterp_': True}
    exec """def f():
        pass""" in d
    assert not pypypolicy.look_inside_function(d['f'])

def test_astcompiler():
    from pypy.interpreter.astcompiler import ast
    assert not pypypolicy.look_inside_function(ast.AST.walkabout)

def test_pyparser():
    from pypy.interpreter.pyparser import parser
    assert not pypypolicy.look_inside_function(parser.Grammar.__init__.im_func)

def test_pypy_module():
    from pypy.module._random.interp_random import W_Random
    assert not pypypolicy.look_inside_function(W_Random.random)
    assert not pypypolicy.look_inside_pypy_module('posix.interp_expat')
    assert pypypolicy.look_inside_pypy_module('__builtin__.operation')
    assert pypypolicy.look_inside_pypy_module('__builtin__.abstractinst')
    assert pypypolicy.look_inside_pypy_module('exceptions.interp_exceptions')
    for modname in 'pypyjit', 'signal', 'micronumpy', 'math':
        assert pypypolicy.look_inside_pypy_module(modname)
        assert pypypolicy.look_inside_pypy_module(modname + '.foo')

def test_see_jit_module():
    assert pypypolicy.look_inside_pypy_module('pypyjit.interp_jit')

def test_module_with_stuff_in_init():
    from pypy.module.sys import Module
    assert not pypypolicy.look_inside_function(Module.getdictvalue.im_func)
