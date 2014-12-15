import os
import re
from collections import namedtuple

# Hacks:
INSTALL_PATH = '/home/david/coding-3/gcc-git-jit-pypy/install'
INCLUDE_DIR = os.path.join(INSTALL_PATH, 'include')
LIB_DIR = os.path.join(INSTALL_PATH, 'lib')
BIN_DIR = os.path.join(INSTALL_PATH, 'bin')

def append_to_envvar_path(envvar, path):
    if envvar in os.environ:
        os.environ[envvar] = path + ':' + os.environ[envvar]
    else:
        os.environ[envvar] = path
    print('%s=%s' % (envvar, os.environ[envvar]))

# It appears that we need to override os.environ['LD_LIBRARY_PATH']
# before importing cffi for it to take account of this.
append_to_envvar_path('LD_LIBRARY_PATH', LIB_DIR)
# actually, for some reason I get:
#  File "/usr/lib64/python2.7/site-packages/cffi/vengine_cpy.py", line 124, in load_library
#    raise ffiplatform.VerificationError(error)
# cffi.ffiplatform.VerificationError: importing '/home/david/coding-3/pypy-libgccjit/rpython/jit/backend/libgccjit/__pycache__/_cffi__x5c2f8978xf4274cdc.so': libgccjit.so.0: cannot open shared object file: No such file or directory
# if LD_LIBRARY_PATH isn't set up before python starts up; issue with imp.load_dynamic ?

# The library requires the correct driver to be in the PATH:
append_to_envvar_path('PATH', BIN_DIR)

os.system('env')

import cffi

ffi = cffi.FFI()

with open(os.path.join(INCLUDE_DIR, 'libgccjit.h')) as f:
    libgccjit_h_content = f.read()

def toy_preprocessor(content):
    """
    ffi.cdef can't handle preprocessor directives.
    We only have the idempotency guards and ifdef __cplusplus;
    strip them out.
    """
    State = namedtuple('State', ('line', 'accepting_text'))
    macros = {}
    result = [] # list of lines
    states = [State('default', accepting_text=True)]
    for line in content.splitlines():
        if 0:
            print(repr(line))

        m = re.match('#ifndef\s+(\S+)', line)
        if m:
            states.append(State(line,
                                accepting_text=(m.group(1) not in macros)) )
            continue
        m = re.match('#ifdef\s+(\S+)', line)

        if m:
            states.append(State(line,
                                accepting_text=(m.group(1) in macros)) )
            continue

        m = re.match('#define\s+(\S+)', line)
        if m:
            macros[m.group(1)] = ''
            continue

        m = re.match('#endif\s*', line)
        if m:
            states.pop()
            continue

        if states[-1].accepting_text:
            result.append(line)

    return '\n'.join(result)
    
libgccjit_h_content = toy_preprocessor(libgccjit_h_content)

# print(libgccjit_h_content)

ffi.cdef(libgccjit_h_content)

lib = ffi.verify('#include "libgccjit.h"',
                 libraries=['gccjit'],
                 library_dirs=[LIB_DIR],
                 include_dirs=[INCLUDE_DIR])

ctxt = lib.gcc_jit_context_acquire()
print ctxt

lib.gcc_jit_context_set_bool_option(ctxt,
        lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
        1)
lib.gcc_jit_context_set_int_option(ctxt,
        lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
        3)
lib.gcc_jit_context_set_bool_option(ctxt,
        lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
        1)
lib.gcc_jit_context_set_bool_option(ctxt,
        lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
        1)
lib.gcc_jit_context_set_bool_option(ctxt,
                                    lib.GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
                                    1)

int_type = lib.gcc_jit_context_get_type(ctxt, lib.GCC_JIT_TYPE_INT)
param = lib.gcc_jit_context_new_param(ctxt, ffi.NULL, int_type, "input")
fn = lib.gcc_jit_context_new_function(ctxt,
                                      ffi.NULL,
                                      lib.GCC_JIT_FUNCTION_EXPORTED,
                                      int_type,
                                      "add_one_to",
                                      1, [param], 0)
v_res = lib.gcc_jit_function_new_local(fn, ffi.NULL, int_type, "v_res")

b_initial = lib.gcc_jit_function_new_block(fn, "initial")

c_one = lib.gcc_jit_context_new_rvalue_from_int(ctxt, int_type, 1)

op_add = lib.gcc_jit_context_new_binary_op(ctxt, ffi.NULL,
                                           lib.GCC_JIT_BINARY_OP_PLUS,
                                           int_type,
                                           lib.gcc_jit_param_as_rvalue(param),
                                           c_one)
lib.gcc_jit_block_add_assignment(b_initial, ffi.NULL,
                                 v_res,
                                 op_add)

lib.gcc_jit_block_end_with_return(b_initial, ffi.NULL,
                                  lib.gcc_jit_lvalue_as_rvalue(v_res))

jit_result = lib.gcc_jit_context_compile(ctxt)

lib.gcc_jit_context_release(ctxt)

fn_ptr = lib.gcc_jit_result_get_code(jit_result, "add_one_to")
if not fn_ptr:
    raise Exception("fn_ptr is NULL")
print('fn_ptr: %r' % fn_ptr)

fn_result = ffi.cast("int(*)(int)", fn_ptr)(41)
print('fn_result: %r' % fn_result)
assert fn_result == 42

lib.gcc_jit_result_release(jit_result)
