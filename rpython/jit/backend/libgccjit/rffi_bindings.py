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
    eci = ExternalCompilationInfo(includes=['stdio.h', 'libgccjit.h'],
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
        self.GCC_JIT_OBJECT_P = lltype.Ptr(COpaque(name='gcc_jit_object',
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
        self.RVALUE_P_P = lltype.Ptr(lltype.Array(self.GCC_JIT_RVALUE_P,
                                                  hints={'nolength': True}))
        self.TYPE_P_P = lltype.Ptr(lltype.Array(self.GCC_JIT_TYPE_P,
                                                hints={'nolength': True}))

        # Entrypoints:
        for returntype, name, paramtypes in [
            (self.GCC_JIT_CONTEXT_P,
             'gcc_jit_context_acquire', []),

            (lltype.Void,
             'gcc_jit_context_release', [self.GCC_JIT_CONTEXT_P]),

            (lltype.Void,
             'gcc_jit_context_set_int_option', [self.GCC_JIT_CONTEXT_P,
                                                # FIXME:
                                                #   enum gcc_jit_int_option:
                                                INT,
                                                INT]),
            (lltype.Void,
             'gcc_jit_context_set_bool_option', [self.GCC_JIT_CONTEXT_P,
                                                 # FIXME:
                                                 # enum gcc_jit_bool_option:
                                                 INT,
                                                 INT]),

            (self.GCC_JIT_RESULT_P,
             'gcc_jit_context_compile', [self.GCC_JIT_CONTEXT_P]),


            (lltype.Void,
             'gcc_jit_context_dump_to_file', [self.GCC_JIT_CONTEXT_P,
                                              CCHARP,
                                              INT]),

            (CCHARP,
             'gcc_jit_context_get_last_error', [self.GCC_JIT_CONTEXT_P]),

            (VOIDP,
             'gcc_jit_result_get_code', [self.GCC_JIT_RESULT_P,
                                         CCHARP]),

            (VOIDP,
             'gcc_jit_result_get_global', [self.GCC_JIT_RESULT_P,
                                           CCHARP]),

            (lltype.Void,
             'gcc_jit_result_release', [self.GCC_JIT_RESULT_P]),

            (CCHARP,
             'gcc_jit_object_get_debug_string', [self.GCC_JIT_OBJECT_P]),

            ############################################################
            # Types
            ############################################################
            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_type_as_object', [self.GCC_JIT_TYPE_P]),

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

            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_field_as_object', [self.GCC_JIT_FIELD_P]),

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

            (self.GCC_JIT_TYPE_P,
             'gcc_jit_context_new_union_type', [self.GCC_JIT_CONTEXT_P,
                                                self.GCC_JIT_LOCATION_P,
                                                CCHARP,
                                                INT,
                                                self.FIELD_P_P]),

            (self.GCC_JIT_TYPE_P,
             'gcc_jit_context_new_function_ptr_type', [self.GCC_JIT_CONTEXT_P,
                                                       self.GCC_JIT_LOCATION_P,
                                                       self.GCC_JIT_TYPE_P,
                                                       INT,
                                                       self.TYPE_P_P,
                                                       INT]),

            ############################################################
            # Constructing functions.
            ############################################################
            (self.GCC_JIT_PARAM_P,
             'gcc_jit_context_new_param', [self.GCC_JIT_CONTEXT_P,
                                           self.GCC_JIT_LOCATION_P,
                                           self.GCC_JIT_TYPE_P,
                                           CCHARP]),
            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_param_as_object', [self.GCC_JIT_PARAM_P]),
            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_param_as_lvalue', [self.GCC_JIT_PARAM_P]),
            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_param_as_rvalue', [self.GCC_JIT_PARAM_P]),

            (self.GCC_JIT_FUNCTION_P,
             'gcc_jit_context_new_function', [self.GCC_JIT_CONTEXT_P,
                                              self.GCC_JIT_LOCATION_P,
                                              # FIXME:
                                              #   enum gcc_jit_function_kind:
                                              INT,
                                              self.GCC_JIT_TYPE_P,
                                              CCHARP,
                                              INT,
                                              self.PARAM_P_P,
                                              INT]),

            (self.GCC_JIT_FUNCTION_P,
             'gcc_jit_context_get_builtin_function', [self.GCC_JIT_CONTEXT_P,
                                                      CCHARP]),

            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_function_as_object', [self.GCC_JIT_FUNCTION_P]),

            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_function_new_local', [self.GCC_JIT_FUNCTION_P,
                                            self.GCC_JIT_LOCATION_P,
                                            self.GCC_JIT_TYPE_P,
                                            CCHARP]),

            (self.GCC_JIT_BLOCK_P,
             'gcc_jit_function_new_block', [self.GCC_JIT_FUNCTION_P,
                                            CCHARP]),
            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_block_as_object', [self.GCC_JIT_BLOCK_P]),

            ############################################################
            # lvalues, rvalues and expressions.
            ############################################################
            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_context_new_global', [self.GCC_JIT_CONTEXT_P,
                                            self.GCC_JIT_LOCATION_P,
                                            # FIXME enum gcc_jit_global_kind:
                                            INT,
                                            self.GCC_JIT_TYPE_P,
                                            CCHARP]),

            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_lvalue_as_object', [self.GCC_JIT_LVALUE_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_lvalue_as_rvalue', [self.GCC_JIT_LVALUE_P]),

            (self.GCC_JIT_OBJECT_P,
             'gcc_jit_rvalue_as_object', [self.GCC_JIT_RVALUE_P]),

            (self.GCC_JIT_TYPE_P,
             'gcc_jit_rvalue_get_type', [self.GCC_JIT_RVALUE_P]),

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
             'gcc_jit_context_new_rvalue_from_double', [self.GCC_JIT_CONTEXT_P,
                                                        self.GCC_JIT_TYPE_P,
                                                        DOUBLE]),
            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_rvalue_from_ptr', [self.GCC_JIT_CONTEXT_P,
                                                     self.GCC_JIT_TYPE_P,
                                                     VOIDP]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_null', [self.GCC_JIT_CONTEXT_P,
                                      self.GCC_JIT_TYPE_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_unary_op', [self.GCC_JIT_CONTEXT_P,
                                              self.GCC_JIT_LOCATION_P,
                                              # FIXME enum gcc_jit_unary_op:
                                              INT,
                                              self.GCC_JIT_TYPE_P,
                                              self.GCC_JIT_RVALUE_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_binary_op', [self.GCC_JIT_CONTEXT_P,
                                               self.GCC_JIT_LOCATION_P,
                                               # FIXME enum gcc_jit_binary_op:
                                               INT,
                                               self.GCC_JIT_TYPE_P,
                                               self.GCC_JIT_RVALUE_P,
                                               self.GCC_JIT_RVALUE_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_comparison', [self.GCC_JIT_CONTEXT_P,
                                                self.GCC_JIT_LOCATION_P,
                                                # FIXME enum gcc_jit_comparison:
                                                INT,
                                                self.GCC_JIT_RVALUE_P,
                                                self.GCC_JIT_RVALUE_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_call', [self.GCC_JIT_CONTEXT_P,
                                          self.GCC_JIT_LOCATION_P,
                                          self.GCC_JIT_FUNCTION_P,
                                          INT,
                                          self.RVALUE_P_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_call_through_ptr',[self.GCC_JIT_CONTEXT_P,
                                                     self.GCC_JIT_LOCATION_P,
                                                     self.GCC_JIT_RVALUE_P,
                                                     INT,
                                                     self.RVALUE_P_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_context_new_cast', [self.GCC_JIT_CONTEXT_P,
                                          self.GCC_JIT_LOCATION_P,
                                          self.GCC_JIT_RVALUE_P,
                                          self.GCC_JIT_TYPE_P]),

            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_context_new_array_access', [self.GCC_JIT_CONTEXT_P,
                                                  self.GCC_JIT_LOCATION_P,
                                                  self.GCC_JIT_RVALUE_P,
                                                  self.GCC_JIT_RVALUE_P]),

            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_lvalue_access_field', [self.GCC_JIT_LVALUE_P,
                                             self.GCC_JIT_LOCATION_P,
                                             self.GCC_JIT_FIELD_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_rvalue_access_field', [self.GCC_JIT_RVALUE_P,
                                             self.GCC_JIT_LOCATION_P,
                                             self.GCC_JIT_FIELD_P]),

            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_rvalue_dereference_field', [self.GCC_JIT_RVALUE_P,
                                                  self.GCC_JIT_LOCATION_P,
                                                  self.GCC_JIT_FIELD_P]),

            (self.GCC_JIT_LVALUE_P,
             'gcc_jit_rvalue_dereference', [self.GCC_JIT_RVALUE_P,
                                            self.GCC_JIT_LOCATION_P]),

            (self.GCC_JIT_RVALUE_P,
             'gcc_jit_lvalue_get_address', [self.GCC_JIT_LVALUE_P,
                                            self.GCC_JIT_LOCATION_P]),

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
            GCC_JIT_GLOBAL_EXPORTED,
            GCC_JIT_GLOBAL_INTERNAL,
            GCC_JIT_GLOBAL_IMPORTED
            """)

        self.make_enum_values(
            """
            GCC_JIT_UNARY_OP_MINUS,
            GCC_JIT_UNARY_OP_BITWISE_NEGATE,
            GCC_JIT_UNARY_OP_LOGICAL_NEGATE,
            GCC_JIT_UNARY_OP_ABS
            """)

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
                    self,
                    self.lib.gcc_jit_context_get_type(self.inner_ctxt,
                                                      r_enum))

    def get_int_type(self, num_bytes, is_signed):
        return Type(self.lib,
                    self,
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
        return Field(self.lib, self, field)

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
        return Struct(self.lib, self, inner_struct)

    def new_opaque_struct(self, name):
        name_charp = str2charp(name)
        inner_struct = self.lib.gcc_jit_context_new_opaque_struct(
            self.inner_ctxt,
            self.lib.null_location_ptr,
            name_charp)
        free_charp(name_charp)
        return Struct(self.lib, self, inner_struct)

    def new_union_type(self, name, fields):
        name_charp = str2charp(name)
        field_array = lltype.malloc(self.lib.FIELD_P_P.TO,
                                    len(fields),
                                    flavor='raw') # of maybe gc?
        for i in range(len(fields)):
            field_array[i] = fields[i].inner_field
        inner_type = (
            self.lib.gcc_jit_context_new_union_type(self.inner_ctxt,
                                                    self.lib.null_location_ptr,
                                                    name_charp,
                                                    r_int(len(fields)),
                                                    field_array))
        lltype.free(field_array, flavor='raw')
        free_charp(name_charp)
        return Type(self.lib, self, inner_type)

    def new_function_ptr_type(self, returntype, param_types, is_variadic):
        raw_type_array = lltype.malloc(self.lib.TYPE_P_P.TO,
                                       len(param_types),
                                       flavor='raw') # of maybe gc?
        for i in range(len(param_types)):
            raw_type_array[i] = param_types[i].inner_type

        type_ = self.lib.gcc_jit_context_new_function_ptr_type(
            self.inner_ctxt,
            self.lib.null_location_ptr,
            returntype.inner_type,
            r_int(len(param_types)),
            raw_type_array,
            is_variadic)
        lltype.free(raw_type_array, flavor='raw')

        return Type(self.lib, self, type_)

    def new_rvalue_from_int(self, type_, llvalue):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_rvalue_from_int(
                          self.inner_ctxt,
                          type_.inner_type,
                          llvalue))

    def new_rvalue_from_long(self, type_, llvalue):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_rvalue_from_long(
                          self.inner_ctxt,
                          type_.inner_type,
                          llvalue))

    def zero(self, numeric_type):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_zero(
                          self.inner_ctxt,
                          numeric_type.inner_type))

    def new_rvalue_from_double(self, type_, llvalue):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_rvalue_from_double(
                          self.inner_ctxt,
                          type_.inner_type,
                          llvalue))

    def new_rvalue_from_ptr(self, type_, llvalue):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_rvalue_from_ptr(
                          self.inner_ctxt,
                          type_.inner_type,
                          llvalue))


    def null(self, pointer_type):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_null(self.inner_ctxt,
                                                    pointer_type.inner_type))

    def new_unary_op(self, op, type_, rvalue):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_unary_op(
                          self.inner_ctxt,
                          self.lib.null_location_ptr,
                          op,
                          type_.inner_type,
                          rvalue.inner_rvalue))

    def new_binary_op(self, op, type_, a, b):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_binary_op(
                          self.inner_ctxt,
                          self.lib.null_location_ptr,
                          op,
                          type_.inner_type,
                          a.inner_rvalue, b.inner_rvalue))

    def new_comparison(self, op, a, b):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_comparison(
                          self.inner_ctxt,
                          self.lib.null_location_ptr,
                          op,
                          a.inner_rvalue, b.inner_rvalue))

    def new_call(self, fn, args):
        raw_arg_array = lltype.malloc(self.lib.RVALUE_P_P.TO,
                                      len(args),
                                      flavor='raw') # of maybe gc?
        for i in range(len(args)):
            raw_arg_array[i] = args[i].inner_rvalue
        rvalue = self.lib.gcc_jit_context_new_call(self.inner_ctxt,
                                                   self.lib.null_location_ptr,
                                                   fn.inner_function,
                                                   r_int(len(args)),
                                                   raw_arg_array)
        lltype.free(raw_arg_array, flavor='raw')
        return RValue(self.lib, self, rvalue)

    def new_call_through_ptr(self, fn_ptr, args):
        raw_arg_array = lltype.malloc(self.lib.RVALUE_P_P.TO,
                                      len(args),
                                      flavor='raw') # of maybe gc?
        for i in range(len(args)):
            raw_arg_array[i] = args[i].inner_rvalue
        rvalue = self.lib.gcc_jit_context_new_call_through_ptr(
            self.inner_ctxt,
            self.lib.null_location_ptr,
            fn_ptr.inner_rvalue,
            r_int(len(args)),
            raw_arg_array)
        lltype.free(raw_arg_array, flavor='raw')
        return RValue(self.lib, self, rvalue)

    def new_param(self, type_, name):
        name_charp = str2charp(name)
        param = self.lib.gcc_jit_context_new_param(self.inner_ctxt,
                                                   self.lib.null_location_ptr,
                                                   type_.inner_type,
                                                   name_charp)
        free_charp(name_charp)
        return Param(self.lib, self, param)

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

        return Function(self.lib, self, fn)

    def get_builtin_function(self, name):
        name_charp = str2charp(name)
        fn = self.lib.gcc_jit_context_get_builtin_function(self.inner_ctxt,
                                                           name_charp)
        free_charp(name_charp)
        return Function(self.lib, self, fn)

    def new_global(self, kind, type_, name):
        name_charp = str2charp(name)
        lvalue = self.lib.gcc_jit_context_new_global(self.inner_ctxt,
                                                     self.lib.null_location_ptr,
                                                     kind,
                                                     type_.inner_type,
                                                     name_charp)
        free_charp(name_charp)
        return LValue(self.lib, self, lvalue)

    def new_cast(self, rvalue, type_):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_cast(
                          self.inner_ctxt,
                          self.lib.null_location_ptr,
                          rvalue.inner_rvalue,
                          type_.inner_type))

    def new_array_access(self, ptr, index):
        return LValue(self.lib,
                      self,
                      self.lib.gcc_jit_context_new_array_access(
                          self.inner_ctxt,
                          self.lib.null_location_ptr,
                          ptr.inner_rvalue,
                          index.inner_rvalue))

class LibgccjitError(Exception):
    def __init__(self, ctxt):
        self.msg = charp2str(ctxt.lib.gcc_jit_context_get_last_error (
            ctxt.inner_ctxt))
        #print('self.msg: %r' % self.msg)

    def __str__(self):
        return self.msg

class Object(Wrapper):
    def __init__(self, lib, ctxt, inner_obj):
        if not inner_obj:
            raise LibgccjitError(ctxt)
        Wrapper.__init__(self, lib)
        self.inner_obj = inner_obj

class Type(Object):
    def __init__(self, lib, ctxt, inner_type):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_type_as_object(inner_type))
        self.inner_type = inner_type

    def get_pointer(self):
        return Type(self.lib,
                    self,
                    self.lib.gcc_jit_type_get_pointer(self.inner_type))

class Field(Object):
    def __init__(self, lib, ctxt, inner_field):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_field_as_object(inner_field))
        self.inner_field = inner_field

class Struct(Object):
    def __init__(self, lib, ctxt, inner_struct):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_type_as_object(
                            lib.gcc_jit_struct_as_type(inner_struct)))
        self.inner_struct = inner_struct

    def as_type(self):
        return Type(self.lib,
                    self,
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

class RValue(Object):
    def __init__(self, lib, ctxt, inner_rvalue):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_rvalue_as_object(inner_rvalue))
        self.inner_rvalue = inner_rvalue

    def get_type(self):
        return Type(self.lib,
                    self,
                    self.lib.gcc_jit_rvalue_get_type(self.inner_rvalue))

    def access_field(self, field):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_rvalue_access_field(
                          self.inner_rvalue,
                          self.lib.null_location_ptr,
                          field.inner_field))

    def dereference_field(self, field):
        return LValue(self.lib,
                      self,
                      self.lib.gcc_jit_rvalue_dereference_field(
                          self.inner_rvalue,
                          self.lib.null_location_ptr,
                          field.inner_field))

    def dereference(self):
        return LValue(self.lib,
                      self,
                      self.lib.gcc_jit_rvalue_dereference(
                          self.inner_rvalue,
                          self.lib.null_location_ptr))

class LValue(Object):
    def __init__(self, lib, ctxt, inner_lvalue):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_lvalue_as_object(inner_lvalue))
        self.inner_lvalue = inner_lvalue

    def as_rvalue(self):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_lvalue_as_rvalue(self.inner_lvalue))

    def access_field(self, field):
        return LValue(self.lib,
                      self,
                      self.lib.gcc_jit_lvalue_access_field (
                          self.inner_lvalue,
                          self.lib.null_location_ptr,
                          field.inner_field))

    def get_address(self):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_lvalue_get_address(
                          self.inner_lvalue,
                          self.lib.null_location_ptr))

class Param(Object):
    def __init__(self, lib, ctxt, inner_param):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_param_as_object(inner_param))
        self.inner_param = inner_param

    def as_rvalue(self):
        return RValue(self.lib,
                      self,
                      self.lib.gcc_jit_param_as_rvalue(self.inner_param))

class Function(Object):
    def __init__(self, lib, ctxt, inner_function):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_function_as_object(inner_function))

        self.inner_function = inner_function

    def new_local(self, type_, name):
        name_charp = str2charp(name)
        local = self.lib.gcc_jit_function_new_local(self.inner_function,
                                                    self.lib.null_location_ptr,
                                                    type_.inner_type,
                                                    name_charp)
        free_charp(name_charp)
        return LValue(self.lib, self, local)

    def new_block(self, name=None):
        if name is not None:
            name_charp = str2charp(name)
        else:
            name_charp = NULL
        block = self.lib.gcc_jit_function_new_block(self.inner_function,
                                                    name_charp)
        if name_charp:
            free_charp(name_charp)
        return Block(self.lib, self, block)

class Block(Object):
    def __init__(self, lib, ctxt, inner_block):
        Object.__init__(self, lib, ctxt,
                        lib.gcc_jit_block_as_object(inner_block))

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

class Result(Object):
    def __init__(self, lib, inner_result):
        Wrapper.__init__(self, lib)
        self.inner_result = inner_result

    def get_code(self, name):
        name_charp = str2charp(name)
        fn_ptr = self.lib.gcc_jit_result_get_code(self.inner_result,
                                                  name_charp)
        free_charp(name_charp)
        return fn_ptr

    def get_global(self, name):
        name_charp = str2charp(name)
        sym_ptr = self.lib.gcc_jit_result_get_global(self.inner_result,
                                                     name_charp)
        free_charp(name_charp)
        return sym_ptr

    def release(self):
        self.lib.gcc_jit_result_release(self.inner_result)
