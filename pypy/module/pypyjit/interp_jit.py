"""This is not the JIT :-)

The pypyjit module helpers set the 'jit_enable' flag on code objects.
The code below makes two identical copies of the interpreter's main
loop, and the flag controls which of them is used.  One of them
(dispatch_jit) is transformed to become a JIT by code elsewhere:
pypy/jit/*
"""
import py
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyframe import PyFrame
from pypy.tool.sourcetools import func_with_new_name


PyCode.jit_enable = False     # new default attribute
super_dispatch = PyFrame.dispatch
super_dispatch_bytecode = PyFrame.dispatch_bytecode


def setup():
    # create dispatch_jit() as a copy of dispatch() in which
    # dispatch_bytecode() has been manually inlined.
    # Do this with py.code.Source manipulations for now.
    src = py.code.Source(super_dispatch)
    CALL_SITE = 'return self.dispatch_bytecode(co_code, next_instr, ec)'
    for i, line in enumerate(src):
        if line.strip() == CALL_SITE:
            break
    else:
        raise Exception("fix me!  call to dispatch_bytecode() not found")

    indent = line[:line.index(CALL_SITE)]

    src2 = py.code.Source(PyFrame.dispatch_bytecode)
    hdr = src2[0].strip()
    assert hdr == 'def dispatch_bytecode(self, co_code, next_instr, ec):'
    src2 = src2[1:].deindent().indent(indent)

    src3 = py.code.Source('%s\n%s\n%s\n' % (src[:i], src2, src[i+1:]))
    #print src3
    d = {}
    exec src3.compile() in super_dispatch.func_globals, d
    PyFrame.dispatch_jit = func_with_new_name(d['dispatch'], 'dispatch_jit')

    class __extend__(PyFrame):

        def dispatch(self, co_code, next_instr, ec):
            if self.pycode.jit_enable:
                return self.dispatch_jit(co_code, next_instr, ec)
            else:
                return super_dispatch(self, co_code, next_instr, ec)

def setup2():
    # TEMPORARY: only patches dispatch_bytecode.
    # make a copy of dispatch_bytecode in which BYTECODE_TRACE_ENABLED is False
    # (hack hack!)
    src2 = py.code.Source(PyFrame.dispatch_bytecode)
    hdr = src2[0].strip()
    assert hdr == 'def dispatch_bytecode(self, co_code, next_instr, ec):'
    src2 = src2[1:].deindent()

    src2 = src2.putaround(
                  "def maker(BYTECODE_TRACE_ENABLED):\n" # no comma here
                  "  def dispatch_jit(self, co_code, next_instr, ec):\n",
                  "#\n" # for indentation :-(
                  "  return dispatch_jit")
    #print src2
    d = {}
    exec src2.compile() in super_dispatch.func_globals, d
    PyFrame.dispatch_jit = d['maker'](BYTECODE_TRACE_ENABLED=False)

    class __extend__(PyFrame):

        def dispatch_bytecode(self, co_code, next_instr, ec):
            if self.pycode.jit_enable:
                return self.dispatch_jit(co_code, next_instr, ec)
            else:
                return super_dispatch_bytecode(self, co_code, next_instr, ec)

setup2()

PORTAL = PyFrame.dispatch_jit

# ____________________________________________________________
#
# Public interface

def enable(space, w_code, w_enabled=True):
    # save the app-level sys.executable in JITInfo, where the machine
    # code backend can fish for it - XXX the following import will look
    # less obscure once codebuf.py is moved to a general
    # processor-independent place
    from pypy.jit.codegen.hlinfo import highleveljitinfo
    if highleveljitinfo.sys_executable is None:
        highleveljitinfo.sys_executable = space.str_w(
            space.sys.get('executable'))

    code = space.interp_w(PyCode, w_code)
    code.jit_enable = space.is_true(w_enabled)
