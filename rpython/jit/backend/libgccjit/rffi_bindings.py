import os

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

from rpython.rtyper.lltypesystem import rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem.rffi import *
from rpython.rtyper.lltypesystem import lltype

def make_eci():
    eci = ExternalCompilationInfo(includes=['libgccjit.h'],
                                  include_dirs=[INCLUDE_DIR],
                                  libraries=['gccjit'],
                                  library_dirs=[LIB_DIR])
    return eci

class Library:
    def __init__(self, eci):
        self.eci = eci

        # Opaque types:
        self.GCC_JIT_CONTEXT_P = lltype.Ptr(COpaque(name='gcc_jit_context',
                                                    compilation_info=eci))
        self.GCC_JIT_RESULT_P = lltype.Ptr(COpaque(name='gcc_jit_result',
                                                   compilation_info=eci))
        self.GCC_JIT_TYPE_P = lltype.Ptr(COpaque(name='gcc_jit_type',
                                                 compilation_info=eci))
        self.GCC_JIT_LOCATION_P = lltype.Ptr(COpaque(name='gcc_jit_location',
                                                     compilation_info=eci))
        self.GCC_JIT_PARAM_P = lltype.Ptr(COpaque(name='gcc_jit_param',
                                                  compilation_info=eci))
        self.GCC_JIT_LVALUE_P = lltype.Ptr(COpaque(name='gcc_jit_lvalue',
                                                  compilation_info=eci))
        self.GCC_JIT_RVALUE_P = lltype.Ptr(COpaque(name='gcc_jit_rvalue',
                                                  compilation_info=eci))
        self.GCC_JIT_FUNCTION_P = lltype.Ptr(COpaque(name='gcc_jit_function',
                                                     compilation_info=eci))
        self.GCC_JIT_BLOCK_P = lltype.Ptr(COpaque(name='gcc_jit_block',
                                                     compilation_info=eci))

        self.PARAM_P_P = lltype.Ptr(lltype.Array(self.GCC_JIT_PARAM_P,
                                                 hints={'nolength': True}))

        # Entrypoints:
        for returntype, name, paramtypes in [
                (self.GCC_JIT_CONTEXT_P,
                 'gcc_jit_context_acquire', []),

                (lltype.Void,
                 'gcc_jit_context_release', [self.GCC_JIT_CONTEXT_P]),

                (lltype.Void,
                 'gcc_jit_context_set_int_option', [self.GCC_JIT_CONTEXT_P,
                                                    INT, # FIXME: enum gcc_jit_int_option opt,
                                                    INT]),
                (lltype.Void,
                 'gcc_jit_context_set_bool_option', [self.GCC_JIT_CONTEXT_P,
                                                     INT, # FIXME: enum gcc_jit_bool_option opt,
                                                     INT]),

                (self.GCC_JIT_RESULT_P,
                 'gcc_jit_context_compile', [self.GCC_JIT_CONTEXT_P]),


                (VOIDP,
                 'gcc_jit_result_get_code', [self.GCC_JIT_RESULT_P,
                                             CCHARP]),

                (lltype.Void,
                 'gcc_jit_result_release', [self.GCC_JIT_RESULT_P]),

                ############################################################
                # Types
                ############################################################
                (self.GCC_JIT_TYPE_P,
                 'gcc_jit_context_get_type', [self.GCC_JIT_CONTEXT_P,
                                              INT]),

                ############################################################
                # Constructing functions.
                ############################################################
                (self.GCC_JIT_PARAM_P,
                 'gcc_jit_context_new_param', [self.GCC_JIT_CONTEXT_P,
                                               self.GCC_JIT_LOCATION_P,
                                               self.GCC_JIT_TYPE_P,
                                               CCHARP]),
                (self.GCC_JIT_LVALUE_P,
                 'gcc_jit_param_as_lvalue', [self.GCC_JIT_PARAM_P]),
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_param_as_rvalue', [self.GCC_JIT_PARAM_P]),

                (self.GCC_JIT_FUNCTION_P,
                 'gcc_jit_context_new_function', [self.GCC_JIT_CONTEXT_P,
                                                  self.GCC_JIT_LOCATION_P,
                                                  INT, # enum gcc_jit_function_kind kind,
                                                  self.GCC_JIT_TYPE_P,
                                                  CCHARP,
                                                  INT,
                                                  self.PARAM_P_P,
                                                  INT]),
                (self.GCC_JIT_LVALUE_P,
                 'gcc_jit_function_new_local', [self.GCC_JIT_FUNCTION_P,
                                                self.GCC_JIT_LOCATION_P,
                                                self.GCC_JIT_TYPE_P,
                                                CCHARP]),

                (self.GCC_JIT_BLOCK_P,
                 'gcc_jit_function_new_block', [self.GCC_JIT_FUNCTION_P,
                                                CCHARP]),

                ############################################################
                # lvalues, rvalues and expressions.
                ############################################################
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_lvalue_as_rvalue', [self.GCC_JIT_LVALUE_P]),

                # Integer constants.
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_rvalue_from_int', [self.GCC_JIT_CONTEXT_P,
                                                         self.GCC_JIT_TYPE_P,
                                                         INT]),
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_zero', [self.GCC_JIT_CONTEXT_P,
                                          self.GCC_JIT_TYPE_P]),
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_one', [self.GCC_JIT_CONTEXT_P,
                                         self.GCC_JIT_TYPE_P]),

                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_binary_op', [self.GCC_JIT_CONTEXT_P,
                                                   self.GCC_JIT_LOCATION_P,
                                                   INT, # enum gcc_jit_binary_op op,
                                                   self.GCC_JIT_TYPE_P,
                                                   self.GCC_JIT_RVALUE_P,
                                                   self.GCC_JIT_RVALUE_P]),

                ############################################################
                # Statement-creation.
                ############################################################
                (lltype.Void,
                 'gcc_jit_block_add_assignment', [self.GCC_JIT_BLOCK_P,
                                                  self.GCC_JIT_LOCATION_P,
                                                  self.GCC_JIT_LVALUE_P,
                                                  self.GCC_JIT_RVALUE_P]),
                (lltype.Void,
                 'gcc_jit_block_end_with_return', [self.GCC_JIT_BLOCK_P,
                                                   self.GCC_JIT_LOCATION_P,
                                                   self.GCC_JIT_RVALUE_P]),
        ]:
            self.add_entrypoint(returntype, name, paramtypes)

        # Enum values:
        self.make_enum_values("""GCC_JIT_STR_OPTION_PROGNAME""")

        self.make_enum_values("""GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL""")

        self.make_enum_values("""GCC_JIT_BOOL_OPTION_DEBUGINFO,
        GCC_JIT_BOOL_OPTION_DUMP_INITIAL_TREE,
        GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
        GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
        GCC_JIT_BOOL_OPTION_DUMP_SUMMARY,
        GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
        GCC_JIT_BOOL_OPTION_SELFCHECK_GC,
        GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
        """)

        self.make_enum_values("""GCC_JIT_TYPE_VOID,
        GCC_JIT_TYPE_VOID_PTR,
        GCC_JIT_TYPE_BOOL,
        GCC_JIT_TYPE_CHAR,
        GCC_JIT_TYPE_SIGNED_CHAR,
        GCC_JIT_TYPE_UNSIGNED_CHAR,
        GCC_JIT_TYPE_SHORT,
        GCC_JIT_TYPE_UNSIGNED_SHORT,
        GCC_JIT_TYPE_INT,
        GCC_JIT_TYPE_UNSIGNED_INT,
        GCC_JIT_TYPE_LONG,
        GCC_JIT_TYPE_UNSIGNED_LONG,
        GCC_JIT_TYPE_LONG_LONG,
        GCC_JIT_TYPE_UNSIGNED_LONG_LONG,
        GCC_JIT_TYPE_FLOAT,
        GCC_JIT_TYPE_DOUBLE,
        GCC_JIT_TYPE_LONG_DOUBLE,
        GCC_JIT_TYPE_CONST_CHAR_PTR,
        GCC_JIT_TYPE_SIZE_T,
        GCC_JIT_TYPE_FILE_PTR,
        GCC_JIT_TYPE_COMPLEX_FLOAT,
        GCC_JIT_TYPE_COMPLEX_DOUBLE,
        GCC_JIT_TYPE_COMPLEX_LONG_DOUBLE""")

        self.make_enum_values("""GCC_JIT_FUNCTION_EXPORTED,
        GCC_JIT_FUNCTION_INTERNAL,
        GCC_JIT_FUNCTION_IMPORTED,
        GCC_JIT_FUNCTION_ALWAYS_INLINE""")

        self.make_enum_values(
            """
            GCC_JIT_BINARY_OP_PLUS,
            GCC_JIT_BINARY_OP_MINUS,
            GCC_JIT_BINARY_OP_MULT,
            GCC_JIT_BINARY_OP_DIVIDE,
            GCC_JIT_BINARY_OP_MODULO,
            GCC_JIT_BINARY_OP_BITWISE_AND,
            GCC_JIT_BINARY_OP_BITWISE_XOR,
            GCC_JIT_BINARY_OP_BITWISE_OR,
            GCC_JIT_BINARY_OP_LOGICAL_AND,
            GCC_JIT_BINARY_OP_LOGICAL_OR,
            GCC_JIT_BINARY_OP_LSHIFT,
            GCC_JIT_BINARY_OP_RSHIFT
            """)

        self.null_location_ptr = lltype.nullptr(self.GCC_JIT_LOCATION_P.TO)


    def add_entrypoint(self, returntype, name, paramtypes):
        setattr(self, name,
                llexternal(name, paramtypes, returntype,
                           compilation_info=self.eci))

    def make_enum_values(self, lines):
        for value, name in enumerate(lines.split(',')):
            name = name.strip()
            if name:
                setattr(self, name, value)
        

