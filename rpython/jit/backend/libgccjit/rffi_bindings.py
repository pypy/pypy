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

def make_param_array(lib, l):
    array = lltype.malloc(lib.PARAM_P_P.TO,
                          len(l),
                          flavor='raw') # of maybe gc?
    for i in range(len(l)):
        array[i] = l[i]
    return array
    # FIXME: don't leak!

def make_field_array(lib, l):
    array = lltype.malloc(lib.FIELD_P_P.TO,
                          len(l),
                          flavor='raw') # of maybe gc?
    for i in range(len(l)):
        array[i] = l[i]
    return array
    # FIXME: don't leak!

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
        self.GCC_JIT_FIELD_P = lltype.Ptr(COpaque(name='gcc_jit_field',
                                                  compilation_info=eci))
        self.GCC_JIT_STRUCT_P = lltype.Ptr(COpaque(name='gcc_jit_struct',
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

        self.FIELD_P_P = lltype.Ptr(lltype.Array(self.GCC_JIT_FIELD_P,
                                                 hints={'nolength': True}))
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


                (lltype.Void,
                 'gcc_jit_context_dump_to_file', [self.GCC_JIT_CONTEXT_P,
                                                  CCHARP,
                                                  INT]),

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

                (self.GCC_JIT_TYPE_P,
                 'gcc_jit_context_get_int_type', [self.GCC_JIT_CONTEXT_P,
                                                  INT,
                                                  INT]),

                (self.GCC_JIT_TYPE_P,
                 'gcc_jit_type_get_pointer', [self.GCC_JIT_TYPE_P]),

                (self.GCC_JIT_FIELD_P,
                 'gcc_jit_context_new_field', [self.GCC_JIT_CONTEXT_P,
                                               self.GCC_JIT_LOCATION_P,
                                               self.GCC_JIT_TYPE_P,
                                               CCHARP]),
                (self.GCC_JIT_STRUCT_P,
                 'gcc_jit_context_new_struct_type', [self.GCC_JIT_CONTEXT_P,
                                                     self.GCC_JIT_LOCATION_P,
                                                     CCHARP,
                                                     INT,
                                                     self.FIELD_P_P]),

                (self.GCC_JIT_STRUCT_P,
                 'gcc_jit_context_new_opaque_struct', [self.GCC_JIT_CONTEXT_P,
                                                       self.GCC_JIT_LOCATION_P,
                                                       CCHARP]),
                (self.GCC_JIT_TYPE_P,
                 'gcc_jit_struct_as_type', [self.GCC_JIT_STRUCT_P]),

                (lltype.Void,
                 'gcc_jit_struct_set_fields', [self.GCC_JIT_STRUCT_P,
                                               self.GCC_JIT_LOCATION_P,
                                               INT,
                                               self.FIELD_P_P]),

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
                 'gcc_jit_context_new_rvalue_from_long', [self.GCC_JIT_CONTEXT_P,
                                                          self.GCC_JIT_TYPE_P,
                                                          LONG]),
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_zero', [self.GCC_JIT_CONTEXT_P,
                                          self.GCC_JIT_TYPE_P]),
                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_one', [self.GCC_JIT_CONTEXT_P,
                                         self.GCC_JIT_TYPE_P]),

                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_rvalue_from_ptr', [self.GCC_JIT_CONTEXT_P,
                                                         self.GCC_JIT_TYPE_P,
                                                         VOIDP]),

                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_binary_op', [self.GCC_JIT_CONTEXT_P,
                                                   self.GCC_JIT_LOCATION_P,
                                                   INT, # enum gcc_jit_binary_op op,
                                                   self.GCC_JIT_TYPE_P,
                                                   self.GCC_JIT_RVALUE_P,
                                                   self.GCC_JIT_RVALUE_P]),

                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_comparison', [self.GCC_JIT_CONTEXT_P,
                                                    self.GCC_JIT_LOCATION_P,
                                                    INT, # enum gcc_jit_binary_op op,
                                                    self.GCC_JIT_RVALUE_P,
                                                    self.GCC_JIT_RVALUE_P]),

                (self.GCC_JIT_RVALUE_P,
                 'gcc_jit_context_new_cast', [self.GCC_JIT_CONTEXT_P,
                                              self.GCC_JIT_LOCATION_P,
                                              self.GCC_JIT_RVALUE_P,
                                              self.GCC_JIT_TYPE_P]),

                (self.GCC_JIT_LVALUE_P,
                 'gcc_jit_rvalue_dereference_field', [self.GCC_JIT_RVALUE_P,
                                                      self.GCC_JIT_LOCATION_P,
                                                      self.GCC_JIT_FIELD_P]),

                ############################################################
                # Statement-creation.
                ############################################################
                (lltype.Void,
                 'gcc_jit_block_add_assignment', [self.GCC_JIT_BLOCK_P,
                                                  self.GCC_JIT_LOCATION_P,
                                                  self.GCC_JIT_LVALUE_P,
                                                  self.GCC_JIT_RVALUE_P]),
                (lltype.Void,
                 'gcc_jit_block_add_comment', [self.GCC_JIT_BLOCK_P,
                                               self.GCC_JIT_LOCATION_P,
                                               CCHARP]),
                (lltype.Void,
                 'gcc_jit_block_end_with_conditional', [self.GCC_JIT_BLOCK_P,
                                                        self.GCC_JIT_LOCATION_P,
                                                        self.GCC_JIT_RVALUE_P,
                                                        self.GCC_JIT_BLOCK_P,
                                                        self.GCC_JIT_BLOCK_P]),
                (lltype.Void,
                 'gcc_jit_block_end_with_jump', [self.GCC_JIT_BLOCK_P,
                                                 self.GCC_JIT_LOCATION_P,
                                                 self.GCC_JIT_BLOCK_P]),
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

        self.make_enum_values(
            """
            GCC_JIT_COMPARISON_EQ,
            GCC_JIT_COMPARISON_NE,
            GCC_JIT_COMPARISON_LT,
            GCC_JIT_COMPARISON_LE,
            GCC_JIT_COMPARISON_GT,
            GCC_JIT_COMPARISON_GE
            """)

        self.null_location_ptr = lltype.nullptr(self.GCC_JIT_LOCATION_P.TO)


    def add_entrypoint(self, returntype, name, paramtypes):
        setattr(self, name,
                llexternal(name, paramtypes, returntype,
                           compilation_info=self.eci,
                           _nowrapper=True))

    def make_enum_values(self, lines):
        for value, name in enumerate(lines.split(',')):
            name = name.strip()
            if name:
                setattr(self, name, r_int(value))

# An object-oriented interfact to the library

class Wrapper:
    def __init__(self, lib):
        self.lib = lib

class Context(Wrapper):
    def __init__(self, lib, inner_ctxt):
        Wrapper.__init__(self, lib)
        self.inner_ctxt = inner_ctxt

    @staticmethod
    def acquire(lib):
        return Context(lib, lib.gcc_jit_context_acquire())

    def release(self):
        self.lib.gcc_jit_context_release(self.inner_ctxt)

    def set_bool_option(self, key, val):
        self.lib.gcc_jit_context_set_bool_option(self.inner_ctxt,
                                                 key, val)

    def set_int_option(self, key, val):
        self.lib.gcc_jit_context_set_int_option(self.inner_ctxt,
                                                key, val)

    def compile(self):
        inner_result = self.lib.gcc_jit_context_compile(self.inner_ctxt)
        if not inner_result:
            # FIXME: get error from context
            raise Exception("result is NULL")
        return Result(self.lib, inner_result)

    def dump_to_file(self, path, update_locations):
        path_charp = str2charp(path)
        self.lib.gcc_jit_context_dump_to_file(self.inner_ctxt,
                                              path_charp,
                                              update_locations)
        free_charp(path_charp)

    def get_type(self, r_enum):
        return Type(self.lib,
                    self.lib.gcc_jit_context_get_type(self.inner_ctxt,
                                                      r_enum))

    def get_int_type(self, num_bytes, is_signed):
        return Type(self.lib,
                    self.lib.gcc_jit_context_get_int_type(self.inner_ctxt,
                                                          num_bytes,
                                                          is_signed))

    def new_field(self, type_, name):
        name_charp = str2charp(name)
        field = self.lib.gcc_jit_context_new_field(self.inner_ctxt,
                                                   self.lib.null_location_ptr,
                                                   type_.inner_type,
                                                   name_charp)
        free_charp(name_charp)
        return Field(self.lib, field)

    def new_struct_type(self, name, fields):
        name_charp = str2charp(name)
        field_array = lltype.malloc(self.lib.FIELD_P_P.TO,
                                    len(fields),
                                    flavor='raw') # of maybe gc?
        for i in range(len(fields)):
            field_array[i] = fields[i].inner_field
        inner_struct = (
            self.lib.gcc_jit_context_new_struct_type(self.inner_ctxt,
                                                     self.lib.null_location_ptr,
                                                     name_charp,
                                                     r_int(len(fields)),
                                                     field_array))
        lltype.free(field_array, flavor='raw')
        free_charp(name_charp)
        return Struct(self.lib, inner_struct)
    
    def new_opaque_struct(self, name):
        name_charp = str2charp(name)
        inner_struct = (
            self.lib.gcc_jit_context_new_opaque_struct(self.inner_ctxt,
                                                       self.lib.null_location_ptr,
                                                       name_charp))
        free_charp(name_charp)
        return Struct(self.lib, inner_struct)

    def new_rvalue_from_int(self, type_, llvalue):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_rvalue_from_int(self.inner_ctxt,
                                                                   type_.inner_type,
                                                                   llvalue))

    def new_rvalue_from_long(self, type_, llvalue):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_rvalue_from_long(self.inner_ctxt,
                                                                    type_.inner_type,
                                                                    llvalue))

    def new_rvalue_from_ptr(self, type_, llvalue):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_rvalue_from_ptr(self.inner_ctxt,
                                                                   type_.inner_type,
                                                                   llvalue))

    def new_binary_op(self, op, type_, a, b):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_binary_op(self.inner_ctxt,
                                                             self.lib.null_location_ptr,
                                                             op,
                                                             type_.inner_type,
                                                             a.inner_rvalue, b.inner_rvalue))

    def new_comparison(self, op, a, b):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_comparison(self.inner_ctxt,
                                                              self.lib.null_location_ptr,
                                                              op,
                                                              a.inner_rvalue, b.inner_rvalue))

    def new_param(self, type_, name):
        name_charp = str2charp(name)
        param = self.lib.gcc_jit_context_new_param(self.inner_ctxt,
                                                   self.lib.null_location_ptr,
                                                   type_.inner_type,
                                                   name_charp)
        free_charp(name_charp)
        return Param(self.lib, param)

    def new_function(self, kind, returntype, name, params, is_variadic):
        name_charp = str2charp(name)
        raw_param_array = lltype.malloc(self.lib.PARAM_P_P.TO,
                                    len(params),
                                    flavor='raw') # of maybe gc?
        for i in range(len(params)):
            raw_param_array[i] = params[i].inner_param

        fn = self.lib.gcc_jit_context_new_function(self.inner_ctxt,
                                                   self.lib.null_location_ptr,
                                                   kind,
                                                   returntype.inner_type,
                                                   name_charp,
                                                   r_int(len(params)),
                                                   raw_param_array,
                                                   is_variadic)
        lltype.free(raw_param_array, flavor='raw')
        free_charp(name_charp)

        return Function(self.lib, fn)

    def new_cast(self, rvalue, type_):
        return RValue(self.lib,
                      self.lib.gcc_jit_context_new_cast(self.inner_ctxt,
                                                        self.lib.null_location_ptr,
                                                        rvalue.inner_rvalue,
                                                        type_.inner_type))

class Type(Wrapper):
    def __init__(self, lib, inner_type):
        Wrapper.__init__(self, lib)
        self.inner_type = inner_type

    def get_pointer(self):
        return Type(self.lib,
                    self.lib.gcc_jit_type_get_pointer(self.inner_type))

class Field(Wrapper):
    def __init__(self, lib, inner_field):
        Wrapper.__init__(self, lib)
        self.inner_field = inner_field

class Struct(Wrapper):
    def __init__(self, lib, inner_struct):
        Wrapper.__init__(self, lib)
        self.inner_struct = inner_struct

    def as_type(self):
        return Type(self.lib,
                    self.lib.gcc_jit_struct_as_type(self.inner_struct))


    def set_fields(self, fields):
        field_array = lltype.malloc(self.lib.FIELD_P_P.TO,
                                    len(fields),
                                    flavor='raw') # of maybe gc?
        for i in range(len(fields)):
            field_array[i] = fields[i].inner_field
        self.lib.gcc_jit_struct_set_fields(self.inner_struct,
                                           self.lib.null_location_ptr,
                                           r_int(len(fields)),
                                           field_array)
        lltype.free(field_array, flavor='raw')

class RValue(Wrapper):
    def __init__(self, lib, inner_rvalue):
        Wrapper.__init__(self, lib)
        self.inner_rvalue = inner_rvalue

    def dereference_field(self, field):
        return LValue(self.lib,
                      self.lib.gcc_jit_rvalue_dereference_field(self.inner_rvalue,
                                                                self.lib.null_location_ptr,
                                                                field.inner_field))

class LValue(Wrapper):
    def __init__(self, lib, inner_lvalue):
        Wrapper.__init__(self, lib)
        self.inner_lvalue = inner_lvalue

    def as_rvalue(self):
        return RValue(self.lib,
                      self.lib.gcc_jit_lvalue_as_rvalue(self.inner_lvalue))

class Param(Wrapper):
    def __init__(self, lib, inner_param):
        Wrapper.__init__(self, lib)
        self.inner_param = inner_param

    def as_rvalue(self):
        return RValue(self.lib,
                      self.lib.gcc_jit_param_as_rvalue(self.inner_param))

class Function(Wrapper):
    def __init__(self, lib, inner_function):
        Wrapper.__init__(self, lib)
        self.inner_function = inner_function

    def new_local(self, type_, name):
        name_charp = str2charp(name)
        local = self.lib.gcc_jit_function_new_local(self.inner_function,
                                                    self.lib.null_location_ptr,
                                                    type_.inner_type,
                                                    name_charp)
        free_charp(name_charp)
        return LValue(self.lib, local)

    def new_block(self, name=None):
        if name is not None:
            name_charp = str2charp(name)
        else:
            name_charp = NULL
        block = self.lib.gcc_jit_function_new_block(self.inner_function,
                                                    name_charp)
        if name_charp:
            free_charp(name_charp)
        return Block(self.lib, block)

class Block(Wrapper):
    def __init__(self, lib, inner_block):
        Wrapper.__init__(self, lib)
        self.inner_block = inner_block

    def add_assignment(self, lvalue, rvalue):
        self.lib.gcc_jit_block_add_assignment(self.inner_block,
                                              self.lib.null_location_ptr,
                                              lvalue.inner_lvalue,
                                              rvalue.inner_rvalue)

    def add_comment(self, text):
        text_charp = str2charp(text)
        self.lib.gcc_jit_block_add_comment(self.inner_block,
                                           self.lib.null_location_ptr,
                                           text_charp)
        free_charp(text_charp)

    def end_with_conditional(self, boolval, on_true, on_false):
        self.lib.gcc_jit_block_end_with_conditional(self.inner_block,
                                                    self.lib.null_location_ptr,
                                                    boolval.inner_rvalue,
                                                    on_true.inner_block,
                                                    on_false.inner_block)

    def end_with_jump (self, target):
        self.lib.gcc_jit_block_end_with_jump (self.inner_block,
                                              self.lib.null_location_ptr,
                                              target.inner_block)

    def end_with_return(self, rvalue):
        self.lib.gcc_jit_block_end_with_return(self.inner_block,
                                               self.lib.null_location_ptr,
                                               rvalue.inner_rvalue)

class Result(Wrapper):
    def __init__(self, lib, inner_result):
        Wrapper.__init__(self, lib)
        self.inner_result = inner_result

    def get_code(self, name):
        name_charp = str2charp(name)
        fn_ptr = self.lib.gcc_jit_result_get_code(self.inner_result,
                                                  name_charp)
        free_charp(name_charp)
        return fn_ptr

    def release(self):
        self.lib.gcc_jit_result_release(self.inner_result)
