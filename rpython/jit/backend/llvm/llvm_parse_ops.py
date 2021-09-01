from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.support import ptr2int
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.jit_libffi import types
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.jit.backend.llvm.guards import *
from rpython.jit.backend.llsupport import gc, jitframe
from rpython.jit.backend.llvm.llvm_api import CString
import sys

class LLVMOpDispatcher:
    def __init__(self, cpu, builder, module, entry, func, jitframe_type,
                 jitframe_subtypes):
        self.cpu = cpu
        self.builder = builder
        self.module = module
        self.func = func
        self.entry = entry
        self.llvm = self.cpu.llvm
        self.jitframe_type = jitframe_type
        self.jitframe_subtypes = jitframe_subtypes
        self.args_size = 0
        self.local_vars_size = 0
        self.jitframe_depth = 0
        self.ssa_vars = {} #map pypy ssa vars to llvm objects
        self.signs = {} #map int values to whether they're signed or not
        self.structs = {} #map struct descrs to LLVMStruct instances
        self.arrays = {} #map array descrs to LLVMStruct instances
        self.labels = {} #map label descrs to their blocks
        self.descr_phis = {} #map label descrs to phi values
        self.forced = False
        self.guard_follows = False
        self.jitframe = self.llvm.GetParam(self.func, 0)
        self.define_constants()
        self.guard_handler = RuntimeCallBackImpl(self)
        self.llvm.PositionBuilderAtEnd(builder, self.entry)

    def define_constants(self):
        self.zero = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 1)
        self.true = self.llvm.ConstInt(self.cpu.llvm_bool_type, 1, 0)
        self.false = self.llvm.ConstInt(self.cpu.llvm_bool_type, 0, 0)
        cstring = CString("prof")
        self.prof_kind_id = self.llvm.GetMDKindID(self.cpu.context,
                                                  cstring.ptr, cstring.len)
        cstring = CString("dereferenceable")
        self.deref_kind_id = self.llvm.GetMDKindID(self.cpu.context,
                                                   cstring.ptr, cstring.len)
        self.max_int = self.llvm.ConstInt(self.cpu.llvm_wide_int,
                                          2**(self.cpu.WORD*8-1)-1, 1)
        self.min_int = self.llvm.ConstInt(self.cpu.llvm_wide_int,
                                          -2**(self.cpu.WORD*8-1), 1)
        self.fabs_intrinsic = self.define_function([self.cpu.llvm_float_type],
                                                   self.cpu.llvm_float_type,
                                                   "llvm.fabs.f64")
        self.stackmap_intrinsic = self.define_function(
            [self.cpu.llvm_int_type, self.cpu.llvm_indx_type],
            self.cpu.llvm_void_type, "llvm.experimental.stackmap", variadic=True
        )
        self.memset_intrinsic = self.define_function(
            [self.cpu.llvm_void_ptr, self.cpu.llvm_char_type,
             self.cpu.llvm_int_type, self.cpu.llvm_bool_type],
            self.cpu.llvm_void_type, "llvm.memset.p0i8.i64"
        )
        self.set_pred_enums()
        self.defined_int_extend_funcs = {}
        self.malloc = self.define_function([self.cpu.llvm_int_type],
                                           self.cpu.llvm_void_ptr,
                                           "malloc_wrapper")
        self.define_malloc_wrapper()
        attributes = ["hot", "willreturn", "nounwind", "norecurse",
                      "nofree"]
        param_attributes = [("noalias", 1), ("nocapture", 1)]
        self.set_attributes(self.func, attributes, param_attributes)

    def set_branch_weights(self, branch, md_name, weight_true, weight_false):
        cstring = CString(md_name)
        branch_weights = self.llvm.MDString(self.cpu.context,
                                            cstring.ptr, cstring.len)
        weight_true_llvm = self.llvm.ValueAsMetadata(
            self.llvm.ConstInt(self.cpu.llvm_indx_type, weight_true, 0))
        weight_false_llvm = self.llvm.ValueAsMetadata(
            self.llvm.ConstInt(self.cpu.llvm_indx_type, weight_false, 0))
        mds = self.rpython_array(
            [branch_weights, weight_true_llvm, weight_false_llvm], self.llvm.MetadataRef
        )
        weights = self.llvm.MDNode(self.cpu.context, mds, 3)
        weights_value = self.llvm.MetadataAsValue(self.cpu.context, weights)
        self.llvm.SetMetadata(branch, self.prof_kind_id, weights_value)
        lltype.free(mds, flavor='raw')

    def set_attributes(self, func, attributes, param_attributes=None):
        cpu_name = self.cpu.assembler.cpu_name
        cpu_features = self.cpu.assembler.cpu_features
        cstring = CString("target-cpu")
        self.llvm.add_function_string_attribute(func, cstring.ptr, cpu_name,
                                                self.cpu.context)
        cstring = CString("target-features")
        self.llvm.add_function_string_attribute(func, cstring.ptr, cpu_features,
                                                self.cpu.context)

        for attr in attributes:
            cstring = CString(attr)
            self.llvm.add_function_attribute(func, cstring.ptr, cstring.len,
                                             self.cpu.context)

        if param_attributes is not None:
            for attr, index in param_attributes:
                cstring = CString(attr)
                self.llvm.add_param_attribute(func, cstring.ptr, cstring.len,
                                              self.cpu.context, index)

    def set_call_attributes(self, call, attributes=None, param_attributes=None,
                            ret_attributes=None):
        if attributes is not None:
            for attr in attributes:
                cstring = CString(attr)
                kind = self.llvm.GetAttributeKindForName(cstring.ptr,
                                                         cstring.len)
                attribute = self.llvm.CreateEnumAttribute(self.cpu.context,
                                                          kind, 0)
                self.llvm.AddCallSiteAttribute(call, -1, attribute)

        if param_attributes is not None:
            for attr, index in param_attributes:
                cstring = CString(attr)
                kind = self.llvm.GetAttributeKindForName(cstring.ptr,
                                                         cstring.len)
                attribute = self.llvm.CreateEnumAttribute(self.cpu.context,
                                                          kind, 0)
                # note that param indecies are 1-indexed
                self.llvm.AddCallSiteAttribute(call, index, attribute)

        if ret_attributes is not None:
            for attr in ret_attributes:
                cstring = CString(attr)
                kind = self.llvm.GetAttributeKindForName(cstring.ptr,
                                                         cstring.len)
                attribute = self.llvm.CreateEnumAttribute(self.cpu.context,
                                                          kind, 0)
                self.llvm.AddCallSiteAttribute(call, 0, attribute)

    def print_error(self):
        sys.stderr.write("Error: Cannot allocate memory")

    def exit_wrapper(self):
        exit(1)

    def define_malloc_wrapper(self):
        cstring = CString("entry")
        entry = self.llvm.AppendBasicBlock(self.cpu.context, self.malloc,
                                           cstring.ptr)
        cstring = CString("success")
        success = self.llvm.AppendBasicBlock(self.cpu.context, self.malloc,
                                             cstring.ptr)
        cstring = CString("error")
        error = self.llvm.AppendBasicBlock(self.cpu.context, self.malloc,
                                           cstring.ptr)

        self.llvm.PositionBuilderAtEnd(self.builder, entry)
        size = self.llvm.GetParam(self.malloc, 0)
        func_int_ptr = self.get_func_ptr(self.cpu.malloc_wrapper,
                                         [lltype.Signed], llmemory.GCREF)
        func_int_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                          func_int_ptr, 0)
        ptr = self.call_function(func_int_ptr_llvm, self.cpu.llvm_void_ptr,
                                 [self.cpu.llvm_int_type], [size], "ptr")
        cstring = CString("malloc_is_not_null")
        is_not_null = self.llvm.BuildIsNotNull(self.builder, ptr, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, is_not_null, success, error)

        self.llvm.PositionBuilderAtEnd(self.builder, error)
        print_ptr = self.get_func_ptr(self.print_error, [lltype.Void],
                                      lltype.Void)
        print_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, print_ptr, 0)
        self.call_function(print_ptr_llvm, self.cpu.llvm_void_type, [], [], "")
        exit_ptr = self.get_func_ptr(self.exit_wrapper, [lltype.Void], lltype.Void)
        exit_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, exit_ptr, 0)
        self.call_function(exit_ptr_llvm, self.cpu.llvm_void_type,[], [], "")
        # llvm doesn't know the above call is an exit so still need a terminator
        self.llvm.BuildRet(self.builder, ptr)

        self.llvm.PositionBuilderAtEnd(self.builder, success)
        self.llvm.BuildRet(self.builder, ptr)

        self.set_branch_weights(branch, "malloc_error_weights", 100, 0)
        attributes = ["inaccessiblememonly", "willreturn", "nounwind",
                      "norecurse", "speculatable"]
        param_attributes = [("noalias", 0)]
        self.set_attributes(self.malloc, attributes, param_attributes)

        self.llvm.PositionBuilderAtEnd(self.builder, self.entry)

    def define_int_extend_func(self, arg_type):
        try:
            return self.defined_int_extend_funcs[arg_type._cast_to_adr()]

        except KeyError:
            func = self.define_function([arg_type], self.cpu.llvm_int_type,
                                        "extend_int")
            llvm_val = self.llvm.GetParam(func, 0)
            cstring = CString("entry")
            entry = self.llvm.AppendBasicBlock(self.cpu.context, func,
                                                cstring.ptr)
            self.llvm.PositionBuilderAtEnd(self.builder, entry)
            zero = self.llvm.ConstInt(arg_type, 0, 1)
            cstring = CString("is_negative")
            is_negative = self.llvm.BuildICmp(self.builder, self.intslt,
                                              llvm_val, zero, cstring.ptr)
            cstring = CString("zext_int")
            zext_int = self.llvm.BuildZExt(self.builder, llvm_val,
                                            self.cpu.llvm_int_type,
                                            cstring.ptr)
            cstring = CString("sext_int")
            sext_int = self.llvm.BuildSExt(self.builder, llvm_val,
                                            self.cpu.llvm_int_type,
                                            cstring.ptr)
            cstring = CString("result")
            if arg_type is self.cpu.llvm_bool_type:
                result = self.llvm.BuildSelect(self.builder, is_negative, zext_int,
                                               sext_int, cstring.ptr)
            else:
                result = self.llvm.BuildSelect(self.builder, is_negative, sext_int,
                                               zext_int, cstring.ptr)

            self.llvm.BuildRet(self.builder, result)

            attributes = ["optnone", "noinline", "norecurse", "nounwind",
                          "willreturn", "speculatable", "readnone"]
            self.set_attributes(func, attributes)

            self.defined_int_extend_funcs[arg_type._cast_to_adr()] = func
            self.llvm.PositionBuilderAtEnd(self.builder, self.entry)
            return func

    def set_pred_enums(self):
        enums = lltype.malloc(self.llvm.CmpEnums, flavor='raw')
        self.llvm.SetCmpEnums(enums)
        self.inteq = enums.inteq
        self.intne = enums.intne
        self.intugt = enums.intugt
        self.intuge = enums.intuge
        self.intult = enums.intult
        self.intule = enums.intule
        self.intsgt = enums.intsgt
        self.intsge = enums.intsge
        self.intslt = enums.intslt
        self.intsle = enums.intsle
        self.realeq = enums.realeq
        self.realne = enums.realne
        self.realgt = enums.realgt
        self.realge = enums.realge
        self.reallt = enums.reallt
        self.realle = enums.realle
        self.realord = enums.realord
        self.uno = enums.uno
        lltype.free(enums, flavor='raw')

    def get_array_elem_type(self, arraydescr, array_ptr, depth):
        itemsize = arraydescr.itemsize
        if arraydescr.is_array_of_floats():
            if itemsize == 8: elem_type = self.cpu.llvm_float_type
            elif itemsize == 4: elem_type = self.cpu.llvm_single_float_type
            else: raise Exception("Unknwon float size")
        elif arraydescr.is_array_of_primitives():
            elem_type = self.llvm.IntType(self.cpu.context,
                                          itemsize*self.cpu.WORD)
        elif arraydescr.is_array_of_pointers():
            elem_type = self.cpu.llvm_void_ptr
        elif arraydescr.is_array_of_structs():
            fields = arraydescr.all_interiorfielddescrs
            sizedescr = fields[0].fielddescr.get_parent_descr()
            interior_struct = self.parse_struct_descr_to_llvm(sizedescr, array_ptr,
                                                              plain=True)
            elem_type = interior_struct.struct_type
            depth += interior_struct.depth
        else:
            raise Exception("Unknown array type")

        return (elem_type, depth)

    def parse_array_descr_to_llvm(self, arraydescr, array_ptr):
        new_array = False
        try:
            llvm_array = self.structs[arraydescr]
            array_ptr_type = self.llvm.PointerType(llvm_array.struct_type, 0)
        except KeyError:
            try:
                llvm_array = self.arrays[arraydescr]
                array_ptr_type = self.llvm.PointerType(llvm_array.array_type, 0)
            except KeyError:
                new_array = True

        if not new_array:
            cstring = CString("array")
            array_ptr = self.llvm.BuildPointerCast(self.builder, array_ptr,
                                                   array_ptr_type, cstring.ptr)
            llvm_array.change_object(array_ptr)
            return llvm_array

        depth = 1 if arraydescr.lendescr is None else 2
        elem_type, depth = self.get_array_elem_type(arraydescr, array_ptr,
                                                    depth)
        array_type = self.llvm.ArrayType(elem_type, 0)

        if arraydescr.lendescr is not None:
            inlined_array_type = array_type
            array_type = self.get_llvm_struct_type([self.cpu.llvm_int_type,
                                                    inlined_array_type])
            array_ptr_type = self.llvm.PointerType(array_type, 0)
            cstring = CString("array")
            array_ptr = self.llvm.BuildPointerCast(self.builder, array_ptr,
                                                   array_ptr_type,
                                                   cstring.ptr)

            arg_types = [self.cpu.llvm_int_type, inlined_array_type]
            llvm_array = LLVMStruct(self, arg_types, depth,
                                    struct=array_ptr,
                                    struct_type=array_type)

            self.structs[arraydescr] = llvm_array
        else:
            array_ptr_type = self.llvm.PointerType(array_type, 0)
            cstring = CString("array")
            array_ptr = self.llvm.BuildPointerCast(self.builder, array_ptr,
                                                   array_ptr_type,
                                                   cstring.ptr)
            llvm_array = LLVMArray(self, elem_type, depth, array=array_ptr,
                                   array_type=array_type)

            self.arrays[arraydescr] = llvm_array

        return llvm_array

    def get_llvm_field_types(self, fielddescrs):
        llvm_types = []
        for fielddescr in fielddescrs:
            flag = fielddescr.flag
            if flag == 'S' or flag == 'U':
                size = fielddescr.field_size
                llvm_types.append(self.llvm.IntType(self.cpu.context,
                                                    size*self.cpu.WORD))
            elif flag == 'F':
                llvm_types.append(self.cpu.llvm_float_type)
            elif flag == 'P':
                llvm_types.append(self.cpu.llvm_void_ptr)
            else:
                print("Unknwon type flag: ", flag)
                assert False

        return llvm_types

    def get_llvm_struct_type(self, subtypes):
        packed = 0
        types = self.rpython_array(subtypes, self.llvm.TypeRef)
        struct_type = self.llvm.StructType(self.cpu.context, types,
                                           len(subtypes), packed)
        lltype.free(types, flavor='raw')

        return struct_type

    def parse_struct_descr_to_llvm(self, sizedescr, struct_ptr, plain=False):
        try:
            llvm_struct = self.structs[sizedescr]
            struct_ptr_type = self.llvm.PointerType(llvm_struct.struct_type, 0)
            cstring = CString("struct")
            struct_ptr = self.llvm.BuildPointerCast(self.builder, struct_ptr,
                                                    struct_ptr_type, cstring.ptr)
            llvm_struct.change_object(struct_ptr)
            return llvm_struct

        except KeyError:
            fields = sizedescr.get_all_fielddescrs()
            subtypes = []
            llvm_subtypes = []
            in_substruct = False
            depth = 1

            if not plain: #we are a root class and have a vtable
                llvm_subtypes.append(self.cpu.llvm_void_ptr)

            i = 0
            while i < len(fields):
                current_sizedescr = fields[i].get_parent_descr()
                if current_sizedescr is not sizedescr:
                    in_substruct = True
                    llvm_subtypes.extend(self.get_llvm_field_types(subtypes))
                    subtypes = []

                    while i < len(fields)-1 and in_substruct:
                        last_sizedescr = current_sizedescr
                        i += 1
                        current_sizedescr = fields[i].get_parent_descr()
                        if current_sizedescr is sizedescr:
                            in_substruct = False
                            llvm_struct = self.parse_struct_descr_to_llvm(
                                last_sizedescr, struct_ptr)
                            llvm_subtypes.extend(llvm_struct.subtypes)
                if in_substruct: # reached end of struct
                    llvm_struct = self.parse_struct_descr_to_llvm(
                        current_sizedescr, struct_ptr)
                    llvm_subtypes.extend(llvm_struct.subtypes)
                    break

                subtypes.append(fields[i])
                i += 1
            llvm_subtypes.extend(self.get_llvm_field_types(subtypes))

            struct_type = self.get_llvm_struct_type(llvm_subtypes)
            struct_ptr_type = self.llvm.PointerType(struct_type, 0)
            cstring = CString("struct")
            struct = self.llvm.BuildPointerCast(self.builder, struct_ptr,
                                                struct_ptr_type, cstring.ptr)

            llvm_struct = LLVMStruct(self, llvm_subtypes, depth, struct=struct,
                                     struct_type=struct_type)
            self.structs[sizedescr] = llvm_struct

            return llvm_struct

    def get_func_ptr(self, func, arg_types, ret_type):
        #takes rpython types
        FPTR = lltype.Ptr(lltype.FuncType(arg_types, ret_type))
        func_ptr = llhelper(FPTR, func)
        return ptr2int(func_ptr)

    def func_ptr_to_int(self, func, FPTR):
        func_ptr = llhelper(FPTR, func)
        return ConstInt(ptr2int(func_ptr))

    def define_function(self, param_types, ret_type, name, variadic=False):
        #takes llvm types
        parameters = self.rpython_array(param_types, self.llvm.TypeRef)
        signature = self.llvm.FunctionType(ret_type, parameters,
                                           len(param_types),
                                           1 if variadic else 0)
        lltype.free(parameters, flavor='raw')
        cstring = CString(name)
        return self.llvm.AddFunction(self.module, cstring.ptr, signature)

    def call_function(self, func_int_ptr, ret_type, arg_types, args, res_name):
        # takes llvm types
        # pass res_name = "" when returning void
        arg_num = len(args)
        arg_types = self.rpython_array(arg_types, self.llvm.TypeRef)
        func_type = self.llvm.FunctionType(ret_type, arg_types,
                                           arg_num, 0)

        func_ptr_type = self.llvm.PointerType(func_type, 0)
        cstring = CString("func_ptr")
        func = self.llvm.BuildIntToPtr(self.builder, func_int_ptr,
                                       func_ptr_type, cstring.ptr)
        arg_array = self.rpython_array(args, self.llvm.ValueRef)

        cstring = CString(res_name)
        res =  self.llvm.BuildCall(self.builder, func, arg_array, arg_num,
                                   cstring.ptr)

        attributes = ["nounwind", "willreturn", "nofree", "norecurse", "nosync"]
        self.set_call_attributes(res, attributes=attributes)

        lltype.free(arg_array, flavor='raw')
        lltype.free(arg_types, flavor='raw')
        return res

    def create_metadata(self, string):
        cstring = CString(string)
        mdstr = self.llvm.MDString(self.cpu.context, cstring.ptr, len(string))
        return self.llvm.MetadataAsValue(self.cpu.context, mdstr)

    def rpython_array(self, args, elem_type):
        array_type = rffi.CArray(elem_type)
        array = lltype.malloc(array_type, n=len(args), flavor='raw')
        for c, arg in enumerate(args):
            array[c] = arg
        return array

    def parse_args(self, args, llvm_types=False):
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.type == 'i':
                    typ = self.cpu.llvm_int_type
                    val = self.llvm.ConstInt(typ, arg.getvalue(), 1)
                    llvm_args.append([val, typ])
                elif arg.type == 'f':
                    typ = self.cpu.llvm_float_type
                    val = self.llvm.ConstFloat(typ, arg.getvalue())
                    llvm_args.append([val, typ])
                elif arg.type == 'r':
                    int_typ = self.cpu.llvm_int_type
                    const_val = arg.getvalue()._cast_to_int()
                    int_val = self.llvm.ConstInt(int_typ, const_val, 0)
                    # if arg.nonnull():
                    #     int_typ = self.cpu.llvm_int_type
                    #     const_val = arg.getvalue()._cast_to_int()
                    #     int_val = self.llvm.ConstInt(int_typ, const_val, 0)
                    # else:
                    #     int_val = self.zero
                    typ = self.cpu.llvm_void_ptr
                    cstring = CString("ptr_arg")
                    val = self.llvm.BuildIntToPtr(self.builder, int_val,
                                                  typ, cstring.ptr)
                    llvm_args.append([val, typ])
            else:
                val = self.ssa_vars[arg]
                if llvm_types: typ = self.llvm.TypeOf(val)
                else: typ = 0
                llvm_args.append([val, typ])
        return llvm_args

    def cast_arg(self, arg, llvm_val):
        if arg.type == 'i':
            return llvm_val
        if arg.type == 'f':
            cstring = CString("arg")
            return self.llvm.BuildBitCast(self.builder, llvm_val,
                                          self.cpu.llvm_float_type, cstring.ptr)
        if arg.type == 'r':
            cstring = CString("arg")
            return self.llvm.BuildIntToPtr(self.builder, llvm_val,
                                           self.cpu.llvm_void_ptr, cstring.ptr)

    def uncast(self, arg, llvm_val):
    #need to put signed ints back in the jitframe
        if arg.type == 'i':
            typ = self.llvm.PrintTypeToString(self.llvm.TypeOf(llvm_val))
            type_string = rffi.constcharp2str(typ)
            bit_size = int(type_string[1:])
            if bit_size < self.cpu.WORD*8: # check which sign extension to do
                if bit_size == 1: arg_type = self.cpu.llvm_bool_type
                elif bit_size == 8: arg_type = self.cpu.llvm_char_type
                elif bit_size == 16: arg_type = self.cpu.llvm_short_type
                elif bit_size == 32: arg_type = self.cpu.llvm_indx_type
                else: raise Exception("Unknwon integer size")

                func = self.define_int_extend_func(arg_type)
                arg_array = self.rpython_array([llvm_val], self.llvm.ValueRef)
                cstring = CString("uncast_res")
                res = self.llvm.BuildCall(self.builder, func, arg_array, 1,
                                           cstring.ptr)
                lltype.free(arg_array, flavor='raw')

                return res

            else:
                return llvm_val

        elif arg.type == 'f':
            cstring = CString("uncast_res")
            return self.llvm.BuildBitCast(self.builder, llvm_val,
                                          self.cpu.llvm_int_type, cstring.ptr)
        else: #arg.type == 'r'
            cstring = CString("uncast_res")
            return self.llvm.BuildPtrToInt(self.builder, llvm_val,
                                           self.cpu.llvm_int_type, cstring.ptr)

    def exit_trace(self, args, descr):
        self.jitframe.set_elem(descr, 1)
        for i in range(len(args)):
            self.jitframe.set_elem(args[i], 7, i+1)
        self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def init_inputargs(self, inputargs):
        cstring = CString("overflow_flag")
        self.overflow = self.llvm.BuildAlloca(self.builder,
                                              self.cpu.llvm_bool_type,
                                              cstring.ptr)
        self.local_vars_size += 1
        self.llvm.BuildStore(self.builder, self.false, self.overflow)
        self.jitframe = LLVMStruct(self, self.jitframe_subtypes, 2,
                                   struct=self.jitframe,
                                   struct_type=self.jitframe_type)

        indecies_array = rffi.CArray(self.llvm.ValueRef)
        indecies = lltype.malloc(indecies_array, n=3, flavor='raw')
        for c, arg in enumerate(inputargs,1):
            arg_uncast = self.jitframe.get_elem(7,c)
            self.ssa_vars[arg] = self.cast_arg(arg, arg_uncast)
            self.args_size += self.cpu.WORD
        lltype.free(indecies, flavor='raw')

    def dispatch_ops(self, inputargs, ops, faildescr=None):
        if faildescr is None:
            self.init_inputargs(inputargs)
        else: #is bridge
            self.guard_handler.patch_guard(faildescr, inputargs)

        self.operations = ops


        for c, op in enumerate(self.operations):
            if op.opnum == 1:
                self.parse_jump(op)

            elif op.opnum == 2:
                self.parse_finish(op)

            elif op.opnum == 4:
                self.parse_label(op)

            elif op.opnum == 7:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_true(op, resume, bailout)

            elif op.opnum == 8:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_false(op, resume, bailout)

            # ops 9 and 10 are vect ops

            elif op.opnum == 11:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_value(op, resume, bailout)

            elif op.opnum == 12:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_class(op, resume, bailout)

            elif op.opnum == 13:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_nonnull(op, resume, bailout)

            elif op.opnum == 14:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_isnull(op, resume, bailout)

            elif op.opnum == 15:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_nonnull_class(op, resume, bailout)

            elif op.opnum == 20:
                if self.guard_follows:
                    # we already parsed this op in a cond_call
                    self.guard_follows = False
                else:
                    resume, bailout = self.guard_handler.setup_guard(op)
                    self.parse_guard_no_exception(op, resume, bailout)

            elif op.opnum == 21:
                if self.guard_follows:
                    # we already parsed this op in a cond_call
                    self.guard_follows = False
                else:
                    resume, bailout = self.guard_handler.setup_guard(op)
                    self.parse_guard_exception(op, resume, bailout)

            elif op.opnum == 22:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_no_overflow(op, resume, bailout)

            elif op.opnum == 23:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_overflow(op, resume, bailout)

            elif op.opnum == 24:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_not_forced(op, resume, bailout)

            elif op.opnum == 25:
                resume, bailout = self.guard_handler.setup_guard(op)
                self.parse_guard_not_forced(op, resume, bailout)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 32:
                self.parse_int_sub(op)

            elif op.opnum == 33:
                self.parse_int_mul(op)

            elif op.opnum == 34:
                self.parse_uint_mul_high(op)

            elif op.opnum == 35:
                self.parse_int_and(op)

            elif op.opnum == 36:
                self.parse_int_or(op)

            elif op.opnum == 37:
                self.parse_int_xor(op)

            elif op.opnum == 38:
                self.parse_int_rshift(op)

            elif op.opnum == 39:
                self.parse_int_lshift(op)

            elif op.opnum == 40:
                self.parse_uint_rshift(op)

            elif op.opnum == 41:
                self.parse_int_sext(op)

            elif op.opnum == 42:
                self.parse_float_add(op)

            elif op.opnum == 43:
                self.parse_float_sub(op)

            elif op.opnum == 44:
                self.parse_float_mul(op)

            elif op.opnum == 45:
                self.parse_float_div(op)

            elif op.opnum == 46:
                self.parse_float_neg(op)

            elif op.opnum == 47:
                self.parse_float_abs(op)

            elif op.opnum == 48:
                self.parse_float_to_int(op)

            elif op.opnum == 49:
                self.parse_int_to_float(op)

            elif op.opnum == 50:
                self.parse_float_to_single_float(op)

            elif op.opnum == 51:
                self.parse_single_float_to_float(op)

            elif op.opnum == 52:
                self.parse_float_bytes_to_long(op)

            elif op.opnum == 53:
                self.parse_long_bytes_to_float(op)

            elif op.opnum == 91:
                self.parse_int_cmp(op, self.intslt)

            elif op.opnum == 92:
                self.parse_int_cmp(op, self.intsle)

            elif op.opnum == 93:
                self.parse_int_cmp(op, self.inteq)

            elif op.opnum == 94:
                self.parse_int_cmp(op, self.intne)

            elif op.opnum == 95:
                self.parse_int_cmp(op, self.intsgt)

            elif op.opnum == 96:
                self.parse_int_cmp(op, self.intsge)

            elif op.opnum == 97:
                self.parse_int_cmp(op, self.intult)

            elif op.opnum == 98:
                self.parse_int_cmp(op, self.intule)

            elif op.opnum == 99:
                self.parse_int_cmp(op, self.intugt)

            elif op.opnum == 100:
                self.parse_int_cmp(op, self.intuge)

            elif op.opnum == 101:
                self.parse_float_cmp(op, self.reallt)

            elif op.opnum == 102:
                self.parse_float_cmp(op, self.realle)

            elif op.opnum == 103:
                self.parse_float_cmp(op, self.realeq)

            elif op.opnum == 104:
                self.parse_float_cmp(op, self.realne)

            elif op.opnum == 105:
                self.parse_float_cmp(op, self.realgt)

            elif op.opnum == 106:
                self.parse_float_cmp(op, self.realge)

            elif op.opnum == 107:
                self.parse_int_is_zero(op)

            elif op.opnum == 108:
                self.parse_int_is_true(op)

            elif op.opnum == 109:
                self.parse_int_neg(op)

            elif op.opnum == 110:
                self.parse_int_invert(op)

            elif op.opnum == 111:
                self.parse_int_force_ge_zero(op)

            elif op.opnum == 112:
                self.parse_same_as(op)

            elif op.opnum == 113:
                self.parse_same_as(op)

            elif op.opnum == 114:
                self.parse_same_as(op)

            elif op.opnum == 115:
                self.parse_ptr_to_int(op)

            elif op.opnum == 116:
                self.parse_int_to_ptr(op)

            elif op.opnum == 117:
                self.parse_ptr_eq(op)

            elif op.opnum == 118:
                self.parse_ptr_ne(op)

            elif op.opnum == 119:
                self.parse_ptr_eq(op)

            elif op.opnum == 120:
                self.parse_ptr_ne(op)

            elif op.opnum == 122:
                self.parse_arraylen_gc(op)

            elif op.opnum == 140:
                self.parse_getarrayitem_gc(op) #r

            elif op.opnum == 141:
                self.parse_getarrayitem_gc(op) #f

            elif op.opnum == 142:
                self.parse_getarrayitem_gc(op) #i

            elif op.opnum == 143:
                self.parse_getarrayitem_raw(op) #f

            elif op.opnum == 144:
                self.parse_getarrayitem_raw(op) #i

            elif op.opnum == 145:
                self.parse_raw_load(op)

            elif op.opnum == 146:
                self.parse_raw_load(op)

            elif op.opnum == 150:
                self.parse_getinteriorfield_gc(op) #r

            elif op.opnum == 151:
                self.parse_getinteriorfield_gc(op) #f

            elif op.opnum == 152:
                self.parse_getinteriorfield_gc(op) #i

            elif op.opnum == 153:
                self.parse_getfield_gc(op) #r

            elif op.opnum == 154:
                self.parse_getfield_gc(op) #f

            elif op.opnum == 155:
                self.parse_getfield_gc(op) #r

            elif op.opnum == 160:
                self.parse_new(op)

            elif op.opnum == 161:
                self.parse_new_with_vtable(op)

            elif op.opnum == 162:
                self.parse_new_array(op)

            elif op.opnum == 163: #boehm inits to 0 by default
                self.parse_new_array(op)

            elif op.opnum == 167:
                self.parse_force_token(op, c)

            elif op.opnum == 176:
                self.parse_setarrayitem_gc(op)

            elif op.opnum == 177:
                self.parse_setarrayitem_raw(op)

            elif op.opnum == 178:
                self.parse_raw_store(op)

            elif op.opnum == 181:
                self.parse_setinteriorfield_gc(op)

            elif op.opnum == 183:
                self.parse_setfield_gc(op)

            elif op.opnum == 184:
                self.parse_zero_array(op)

            elif op.opnum == 191:
                pass # noop

            elif op.opnum == 193:
                pass # noop

            elif op.opnum == 208:
                self.parse_save_exception(op)

            elif op.opnum == 209:
                self.parse_save_exc_class(op)

            elif op.opnum == 210:
                self.parse_restore_exception(op)

            elif op.opnum == 213:
                self.parse_call(op, 'r')

            elif op.opnum == 214:
                self.parse_call(op, 'f')

            elif op.opnum == 215:
                self.parse_call(op, 'i')

            elif op.opnum == 216:
                self.parse_call(op, 'n')

            elif op.opnum == 217:
                self.parse_cond_call(op, c)

            elif op.opnum == 218:
                self.parse_cond_call_value(op, "r")

            elif op.opnum == 219:
                self.parse_cond_call_value(op, "i")

            elif op.opnum == 220:
                self.parse_call_assembler(op, 'r')

            elif op.opnum == 221:
                self.parse_call_assembler(op, 'f')

            elif op.opnum == 222:
                self.parse_call_assembler(op, 'i')

            elif op.opnum == 223:
                self.parse_call_assembler(op, 'n')

            elif op.opnum == 224:
                self.parse_call(op, "r")

            elif op.opnum == 225:
                self.parse_call(op, "f")

            elif op.opnum == 226:
                self.parse_call(op, "i")

            elif op.opnum == 227:
                self.parse_call(op, "n")

            elif op.opnum == 232:
                self.parse_call_release_gil(op, "f")

            elif op.opnum == 233:
                self.parse_call_release_gil(op, "i")

            elif op.opnum == 234:
                self.parse_call_release_gil(op, "n")

            elif op.opnum == 246:
                self.parse_int_ovf(op, '+')

            elif op.opnum == 247:
                self.parse_int_ovf(op, '-')

            elif op.opnum == 248:
                self.parse_int_ovf(op, '*')

            else: #TODO: take out as this may prevent jump table optimisation
                raise Exception("Unimplemented opcode: "+str(op)+"\n Opnum: "+str(op.opnum))

        self.guard_handler.finalise_bailout()
        if self.cpu.debug:
           self.llvm.DumpModule(self.module)

    def parse_jump(self, op):
        current_block = self.llvm.GetInsertBlock(self.builder)
        descr = op.getdescr()
        target_block = self.labels[descr]
        phis = self.descr_phis[descr]

        c = 0
        for arg, _, in self.parse_args(op.getarglist()):
            phi = phis[c]
            self.llvm.AddIncoming(phi, arg, current_block)
            c += 1

        self.llvm.BuildBr(self.builder, target_block)

    def parse_finish(self, op):
        uncast_args = []
        args = op.getarglist()
        llvm_args = [arg for arg, _ in self.parse_args(args)]
        for arg, llvm_arg in zip(args, llvm_args):
            uncast = self.uncast(arg, llvm_arg)
            uncast_args.append(uncast)
        descr = op.getdescr()
        self.cpu.descr_tokens[self.cpu.descr_token_cnt] = descr
        descr_token = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                         self.cpu.descr_token_cnt, 0)
        self.cpu.descr_token_cnt += 1
        self.exit_trace(uncast_args, descr_token)

    def parse_label(self, op):
        descr = op.getdescr()
        current_block = self.llvm.GetInsertBlock(self.builder)
        cstring = CString("loop_header")
        loop_header = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                 cstring.ptr)
        self.llvm.BuildBr(self.builder, loop_header) #llvm requires explicit branching even for fall through

        self.llvm.PositionBuilderAtEnd(self.builder, loop_header)
        phis = []
        arg_list = op.getarglist()
        c = 0
        for arg, typ in self.parse_args(arg_list, llvm_types=True):
            cstring = CString("phi_"+str(c))
            phi = self.llvm.BuildPhi(self.builder, typ, cstring.ptr)
            self.llvm.AddIncoming(phi, arg, current_block)
            rpy_val = arg_list[c] #want to replace referances to this value with the phi instead of whatever was there beofre
            self.ssa_vars[rpy_val] = phi
            phis.append(phi)
            c += 1

        self.descr_phis[descr] = phis
        self.labels[descr] = loop_header

    def parse_guard_true(self, op, resume, bailout):
        cnd = self.ssa_vars[op.getarglist()[0]]
        cstring = CString("cnd")
        cnd = self.llvm.BuildIntCast(self.builder, cnd, self.cpu.llvm_bool_type,
                                     0, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_false(self, op, resume, bailout):
        cnd = self.ssa_vars[op.getarglist()[0]]
        cstring = CString("cnd")
        cnd = self.llvm.BuildIntCast(self.builder, cnd, self.cpu.llvm_bool_type,
                                     0, cstring.ptr)
        cstring = CString("cnd_flipped")
        cnd_flipped = self.llvm.BuildXor(self.builder, cnd, self.true,
                                         cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd_flipped, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd_flipped, branch)

    def parse_guard_value(self, op, resume, bailout):
        args = op.getarglist()
        val = self.ssa_vars[args[0]]
        typ = args[1].type
        const_val = args[1].getvalue()
        cstring = CString("guard_value_cmp")
        if typ == 'i':
            const = self.llvm.ConstInt(self.cpu.llvm_int_type, const_val, 1)
            cnd = self.llvm.BuildICmp(self.builder, self.inteq, val, const,
                                      cstring.ptr)
        elif typ == 'f':
            const = self.llvm.ConstFloat(self.cpu.llvm_float_type,
                                         float(const_val))
            cnd = self.llvm.BuildFCmp(self.builder, self.realeq, val, const,
                                      cstring.ptr)
        elif typ == 'r':
            const = self.llvm.ConstInt(self.cpu.llvm_int_type, const_val, 0)
            int_ptr = self.llvm.BuildPtrToInt(self.builder, val,
                                              self.cpu.llvm_int_type,
                                              cstring.ptr)
            cnd = self.llvm.BuildICmp(self.builder, self.inteq, int_ptr, const,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_class(self, op, resume, bailout):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        struct = args[0]
        vtable = args[1]

        cstring = CString("struct_cast")
        struct_cast = self.llvm.BuildPointerCast(self.builder, struct,
                                                 self.cpu.llvm_void_ptr,
                                                 cstring.ptr)
        cstring = CString("vtable")
        struct_vtable = self.llvm.BuildLoad(self.builder,
                                            self.cpu.llvm_void_ptr, struct_cast,
                                            cstring.ptr)
        cstring = CString("vtable_cmp")
        ptrdiff = self.llvm.BuildPtrDiff(self.builder, struct_vtable, vtable,
                                         cstring.ptr)
        cstring = CString("guard_class")
        cnd = self.llvm.BuildICmp(self.builder, self.inteq, ptrdiff, self.zero,
                                  cstring.ptr)

        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_nonnull(self, op, resume, bailout):
        arg, typ = self.parse_args(op.getarglist())[0]
        cstring = CString("guard_nonnull_res")
        if typ != 'f': #IsNotNull is generic on int and ptr but not float
            cnd = self.llvm.BuildIsNotNull(self.builder, arg, cstring.ptr)
        else:
            zero = self.llvm.ConstFloat(self.cpu.llvm_float_type, float(0))
            cnd = self.llvm.BuildFCmp(self.builder, self.realne, arg, zero,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_isnull(self, op, resume, bailout):
        arg, typ = self.parse_args(op.getarglist())[0]
        cstring = CString("guard_isnull_res")
        if typ != 'f':
            cnd = self.llvm.BuildIsNull(self.builder, arg, cstring.ptr)
        else:
            zero = self.llvm.ConstFloat(self.cpu.llvm_float_type, float(0))
            cnd = self.llvm.BuildFCmp(self.builder, self.realeq, arg, zero,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_nonnull_class(self, op, resume, bailout):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        struct = args[0]
        vtable = args[1]

        cstring = CString("is_null")
        is_null = self.llvm.BuildIsNull(self.builder, struct, cstring.ptr)

        cstring = CString("struct_cast")
        void_ptr_ptr = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        struct_cast = self.llvm.BuildPointerCast(self.builder, struct,
                                                 void_ptr_ptr,
                                                 cstring.ptr)
        cstring = CString("vtable")
        struct_vtable = self.llvm.BuildLoad(self.builder,
                                            self.cpu.llvm_void_ptr, struct_cast,
                                            cstring.ptr)
        cstring = CString("vtable_cmp")
        ptrdiff = self.llvm.BuildPtrDiff(self.builder, struct_vtable, vtable,
                                         cstring.ptr)
        cstring = CString("is_zero")
        is_zero = self.llvm.BuildICmp(self.builder, self.inteq, ptrdiff,
                                      self.zero, cstring.ptr)
        cstring = CString("guard_class")
        cnd = self.llvm.BuildSelect(self.builder, is_null, self.false, is_zero,
                                    cstring.ptr)

        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_no_exception(self, op, resume, bailout):
        exception_vtable_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                       self.cpu.pos_exception(),
                                                       0)
        ptr_ptr_type = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        cstring = CString("exception_vtable_addr")
        exception_vtable_addr = self.llvm.BuildIntToPtr(self.builder,
                                                        exception_vtable_addr_int,
                                                        ptr_ptr_type, cstring.ptr)
        cstring = CString("exception_vtable")
        exception_vtable = self.llvm.BuildLoad(self.builder,
                                               self.cpu.llvm_void_ptr,
                                               exception_vtable_addr,
                                               cstring.ptr)

        exception_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                self.cpu.pos_exc_value(), 0)
        cstring = CString("exception_addr")
        exception_addr = self.llvm.BuildIntToPtr(self.builder, exception_addr_int,
                                                 ptr_ptr_type, cstring.ptr)
        cstring = CString("exception")
        exception = self.llvm.BuildLoad(self.builder, self.cpu.llvm_void_ptr,
                                        exception_addr, cstring.ptr)

        cstring = CString("null_ptr")
        null_ptr = self.llvm.BuildIntToPtr(self.builder, self.zero,
                                           self.cpu.llvm_void_ptr,
                                           cstring.ptr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_vtable_addr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_addr)

        cstring = CString("guard_exception")
        ptr_diff = self.llvm.BuildPtrDiff(self.builder, exception_vtable,
                                          null_ptr, cstring.ptr)
        cstring = CString("cnd")
        cnd = self.llvm.BuildICmp(self.builder, self.inteq, ptr_diff,
                                  self.zero, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)

        self.llvm.PositionBuilderAtEnd(self.builder, bailout)
        self.jitframe.set_elem(exception, 5)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_exception(self, op, resume, bailout):
        vtable_int = self.parse_args(op.getarglist())[0][0]
        cstring = CString("ptr")
        vtable = self.llvm.BuildIntToPtr(self.builder, vtable_int,
                                         self.cpu.llvm_void_ptr, cstring.ptr)
        exception_vtable_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                       self.cpu.pos_exception(),
                                                       0)
        ptr_ptr_type = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        cstring = CString("exception_vtable_addr")
        exception_vtable_addr = self.llvm.BuildIntToPtr(self.builder,
                                                        exception_vtable_addr_int,
                                                        ptr_ptr_type, cstring.ptr)
        cstring = CString("exception_vtable")
        exception_vtable = self.llvm.BuildLoad(self.builder,
                                               self.cpu.llvm_void_ptr,
                                               exception_vtable_addr,
                                               cstring.ptr)

        exception_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                self.cpu.pos_exc_value(), 0)
        cstring = CString("exception_addr")
        exception_addr = self.llvm.BuildIntToPtr(self.builder, exception_addr_int,
                                                 ptr_ptr_type, cstring.ptr)
        cstring = CString("exception")
        exception = self.llvm.BuildLoad(self.builder, self.cpu.llvm_void_ptr,
                                        exception_addr, cstring.ptr)

        cstring = CString("null_ptr")
        null_ptr = self.llvm.BuildIntToPtr(self.builder, self.zero,
                                           self.cpu.llvm_void_ptr,
                                           cstring.ptr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_vtable_addr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_addr)

        cstring = CString("guard_exception")
        ptr_diff = self.llvm.BuildPtrDiff(self.builder, exception_vtable,
                                          vtable, cstring.ptr)
        cstring = CString("cnd")
        cnd = self.llvm.BuildICmp(self.builder, self.inteq, ptr_diff,
                                  self.zero, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)

        self.llvm.PositionBuilderAtEnd(self.builder, bailout)
        self.jitframe.set_elem(exception, 5)

        self.guard_handler.finalise_guard(op, resume, cnd, branch)
        self.ssa_vars[op] = exception

    def parse_guard_no_overflow(self, op, resume, bailout):
        cstring = CString("overflow_flag")
        cnd = self.llvm.BuildLoad(self.builder, self.cpu.llvm_bool_type,
                                  self.overflow, cstring.ptr)
        cstring = CString("overflow_flag_flipped")
        cnd_flipped = self.llvm.BuildXor(self.builder, cnd, self.true,
                                         cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd_flipped, resume,
                                       bailout)
        self.guard_handler.finalise_guard(op, resume, cnd_flipped, branch)

    def parse_guard_overflow(self, op, resume, bailout):
        cstring = CString("overflow_flag")
        cnd = self.llvm.BuildLoad(self.builder, self.cpu.llvm_bool_type,
                                  self.overflow, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_guard_not_forced(self, op, resume, bailout):
        # assumes only one guard_not_force matches with each force_token
        if self.forced:
            jf_descr = self.jitframe.get_elem(1) #reads out token
            self.forced = False
        else:
            descr = op.getdescr()
            self.cpu.descr_tokens[self.cpu.descr_token_cnt] = descr
            jf_descr = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                          self.cpu.descr_token_cnt, 0)
            self.cpu.descr_token_cnt += 1
        cstring = CString("guard_not_forced")
        force_descr = self.jitframe.get_elem(2)
        cnd = self.llvm.BuildICmp(self.builder, self.intne, jf_descr,
                                  force_descr, cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)
        self.guard_handler.finalise_guard(op, resume, cnd, branch)

    def parse_int_add(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_add_res")
        self.ssa_vars[op] = self.llvm.BuildAdd(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_sub(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_sub_res")
        self.ssa_vars[op] = self.llvm.BuildSub(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_mul(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_mul_res")
        self.ssa_vars[op] = self.llvm.BuildMul(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_uint_mul_high(self, op):
        # see jit/metainterp/optimizeopt/intdiv.py for a more readable version
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        shift = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                   self.cpu.WORD*4, 0)
        mask_tmp = (1 << self.cpu.WORD*4) - 1
        mask = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  mask_tmp, 0)

        cstring = CString("a_high")
        a_high = self.llvm.BuildURShl(self.builder, lhs, shift, cstring.ptr)
        cstring = CString("a_low")
        a_low = self.llvm.BuildAnd(self.builder, lhs, mask, cstring.ptr)
        cstring = CString("b_high")
        b_high = self.llvm.BuildURShl(self.builder, rhs, shift, cstring.ptr)
        cstring = CString("b_low")
        b_low = self.llvm.BuildAnd(self.builder, rhs, mask, cstring.ptr)

        cstring = CString("res_low_low")
        res_low_low = self.llvm.BuildMul(self.builder, a_low, b_low,
                                         cstring.ptr)
        cstring = CString("res_low_high")
        res_low_high = self.llvm.BuildMul(self.builder, a_low, b_high,
                                          cstring.ptr)
        cstring = CString("res_high_low")
        res_high_low = self.llvm.BuildMul(self.builder, a_high, b_low,
                                          cstring.ptr)
        cstring = CString("res_high_high")
        res_high_high = self.llvm.BuildMul(self.builder, a_high, b_high,
                                           cstring.ptr)

        cstring = CString("res")
        res_1_tmp = self.llvm.BuildURShl(self.builder, res_low_low, shift,
                                     cstring.ptr)
        res_1 = self.llvm.BuildAdd(self.builder, res_1_tmp, res_high_low,
                                   cstring.ptr)
        res_2 = self.llvm.BuildAdd(self.builder, res_1, res_low_high,
                                   cstring.ptr)

        cstring = CString("borrow_cnd")
        borrow_cnd = self.llvm.BuildICmp(self.builder, self.intult,
                                         res_2, res_1, cstring.ptr)
        one = self.llvm.ConstInt(self.cpu.llvm_int_type, 1, 0)
        cstring = CString("shifted")
        shifted = self.llvm.BuildLShl(self.builder, one, shift,
                                      cstring.ptr)
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 0)
        cstring = CString("borrow")
        borrow = self.llvm.BuildSelect(self.builder, borrow_cnd,
                                       shifted, zero, cstring.ptr)

        cstring = CString("res")
        res_3 = self.llvm.BuildURShl(self.builder, res_2, shift, cstring.ptr)
        res_4 = self.llvm.BuildAdd(self.builder, res_3, borrow, cstring.ptr)
        self.ssa_vars[op] = self.llvm.BuildAdd(self.builder, res_4,
                                               res_high_high, cstring.ptr)

    def parse_int_and(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_and_res")
        self.ssa_vars[op] = self.llvm.BuildAnd(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_or(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_or_res")
        self.ssa_vars[op] = self.llvm.BuildOr(self.builder, lhs, rhs,
                                              cstring.ptr)

    def parse_int_xor(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_xor_res")
        self.ssa_vars[op] = self.llvm.BuildXor(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_rshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_rshift_res")
        self.ssa_vars[op] = self.llvm.BuildRShl(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_int_lshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_lshift_res")
        self.ssa_vars[op] = self.llvm.BuildLShl(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_uint_rshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("uint_rshift_res")
        self.ssa_vars[op] = self.llvm.BuildURShl(self.builder, lhs, rhs,
                                                 cstring.ptr)

    def parse_int_sext(self, op):
        # args = [arg for arg, _ in self.parse_args(op.getarglist())]
        # num = args[0]
        # num_bytes = args[1]

        # int_type = self.llvm.IntType(self.cpu.context, num_bytes*self.cpu.WORD)
        # cstring = CString("int_sext_res")
        # self.ssa_vars[op] = self.llvm.BuildSExt(self.builder, num, int_type,
        #                                         cstring.ptr)
        raise Exception("Unimplemented")

    def parse_float_add(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_add_res")
        self.ssa_vars[op] = self.llvm.BuildFAdd(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_sub(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_sub_res")
        self.ssa_vars[op] = self.llvm.BuildFSub(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_mul(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_mul_res")
        self.ssa_vars[op] = self.llvm.BuildFMul(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_div(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_div_res")
        self.ssa_vars[op] = self.llvm.BuildFDiv(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_neg(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_neg_res")
        self.ssa_vars[op] = self.llvm.BuildFNeg(self.builder, arg, cstring.ptr)

    def parse_float_abs(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        arg_array_type = rffi.CArray(self.llvm.ValueRef)
        arg_array = lltype.malloc(arg_array_type, n=1, flavor='raw')
        arg_array[0] = arg
        cstring = CString("float_abs_res")
        self.ssa_vars[op] = self.llvm.BuildCall(self.builder,
                                                self.fabs_intrinsic,
                                                arg_array, 1, cstring.ptr)
        lltype.free(arg_array, flavor='raw')

    def parse_float_to_int(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_to_int_res")
        zero = self.llvm.ConstFloat(self.cpu.llvm_float_type, 0)
        cstring = CString("is_negative")
        is_negative = self.llvm.BuildFCmp(self.builder, self.realle, arg,
                                          zero, cstring.ptr)
        cstring = CString("float_to_signed")
        float_to_signed = self.llvm.BuildFPToSI(self.builder, arg,
                                                self.cpu.llvm_int_type,
                                                cstring.ptr)
        cstring = CString("float_to_unsigned")
        float_to_unsigned = self.llvm.BuildFPToUI(self.builder, arg,
                                                  self.cpu.llvm_int_type,
                                                  cstring.ptr)
        cstring = CString("float_to_int_res")
        self.ssa_vars[op] = self.llvm.BuildSelect(self.builder, is_negative,
                                                  float_to_signed,
                                                  float_to_unsigned,
                                                  cstring.ptr)

    def parse_float_bytes_to_long(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_bytes_to_long_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_int_type,
                                                   cstring.ptr)

    def parse_long_bytes_to_float(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_bytes_to_long_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_float_type,
                                                   cstring.ptr)

    def parse_int_to_float(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_to_int_res")
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 1)
        cstring = CString("is_negative")
        is_negative = self.llvm.BuildICmp(self.builder, self.intsle, arg,
                                          zero, cstring.ptr)
        cstring = CString("signed_to_float")
        signed_to_float = self.llvm.BuildSIToFP(self.builder, arg,
                                                self.cpu.llvm_float_type,
                                                cstring.ptr)
        cstring = CString("unsigned_to_float")
        unsigned_to_float = self.llvm.BuildUIToFP(self.builder, arg,
                                                  self.cpu.llvm_float_type,
                                                  cstring.ptr)
        cstring = CString("int_to_float_res")
        self.ssa_vars[op] = self.llvm.BuildSelect(self.builder, is_negative,
                                                  signed_to_float,
                                                  unsigned_to_float,
                                                  cstring.ptr)

    def parse_float_to_single_float(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("float_to_single_float_res")
        self.ssa_vars[op] = self.llvm.FloatTrunc(self.builder, arg,
                                                 self.cpu.llvm_single_float_type,
                                                 cstring.ptr)

    def parse_single_float_to_float(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("single_float_to_res")
        self.ssa_vars[op] = self.llvm.FloatExt(self.builder, arg,
                                               self.cpu.llvm_float_type,
                                               cstring.ptr)

    def parse_int_cmp(self, op, pred):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_cmp_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, lhs, rhs,
                                                cstring.ptr)


    def parse_float_cmp(self, op, pred):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]

        cstring = CString("float_cmp_res")
        cmp = self.llvm.BuildFCmp(self.builder, pred, lhs, rhs,
                                  cstring.ptr)

        if pred == self.realeq:
            cstring = CString("is_nan")
            is_nan = self.llvm.BuildFCmp(self.builder, self.uno, lhs, rhs,
                                         cstring.ptr)
            cstring = CString("float_cmp_res")
            cmp = self.llvm.BuildSelect(self.builder, is_nan, self.false, cmp,
                                        cstring.ptr)
        elif pred == self.realne:
            cstring = CString("is_nan")
            is_nan = self.llvm.BuildFCmp(self.builder, self.uno, lhs, rhs,
                                         cstring.ptr)
            cstring = CString("float_cmp_res")
            cmp = self.llvm.BuildSelect(self.builder, is_nan, self.true, cmp,
                                        cstring.ptr)

        self.ssa_vars[op] = cmp


    def parse_int_is_zero(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_is_zero_res")
        pred = self.inteq
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg,
                                                self.zero, cstring.ptr)

    def parse_int_is_true(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_is_true_res")
        pred = self.intne
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg,
                                                self.zero, cstring.ptr)

    def parse_int_neg(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_neg_res")
        self.ssa_vars[op] = self.llvm.BuildNeg(self.builder, arg, cstring.ptr)

    def parse_int_invert(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        negative_one = self.llvm.ConstInt(self.cpu.llvm_int_type, -1, 1)
        cstring = CString("int_invert_res")
        self.ssa_vars[op] = self.llvm.BuildXor(self.builder, arg, negative_one,
                                               cstring.ptr)

    def parse_int_force_ge_zero(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_force_ge_zero_cmp")
        cmp = self.llvm.BuildICmp(self.builder, self.intsle, arg, self.zero,
                                  cstring.ptr)
        cstring = CString("int_force_ge_zero_res")
        self.ssa_vars[op] = self.llvm.BuildSelect(self.builder, cmp,
                                                  self.zero, arg, cstring.ptr)

    def parse_same_as(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        self.ssa_vars[op] = arg

    def parse_ptr_to_int(self, op):
        arg = op.getarglist()[0]
        if arg.is_constant():
            self.ssa_vars[op] = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                   arg.getvalue(), 0)
        else:
            cstring = CString("pre_to_int_res")
            self.ssa_vars[op] = self.llvm.BuildPtrToInt(self.builder,
                                                        self.ssa_vars[arg],
                                                        self.cpu.llvm_int_type,
                                                        cstring.ptr)

    def parse_int_to_ptr(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_to_ptr_res")
        self.ssa_vars[op] = self.llvm.BuildIntToPtr(self.builder, arg,
                                                    self.cpu.llvm_void_ptr,
                                                    cstring.ptr)

    def parse_ptr_eq(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cstring = CString("ptr")
        lhs = self.llvm.BuildIntToPtr(self.builder, args[0],
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        rhs = self.llvm.BuildIntToPtr(self.builder, args[1],
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        cstring = CString("ptr_eq_res_diff")
        res = self.llvm.BuildPtrDiff(self.builder, lhs, rhs, cstring.ptr)
        cstring = CString("ptr_eq_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, self.inteq,
                                                res, self.zero, cstring.ptr)

    def parse_ptr_ne(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cstring = CString("ptr")
        lhs = self.llvm.BuildIntToPtr(self.builder, args[0],
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        rhs = self.llvm.BuildIntToPtr(self.builder, args[1],
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        cstring = CString("ptr_ne_res_diff")
        res = self.llvm.BuildPtrDiff(self.builder, lhs, rhs, cstring.ptr)
        cstring = CString("ptr_ne_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, self.intne,
                                                res, self.zero, cstring.ptr)

    def parse_arraylen_gc(self, op):
        array = self.parse_args(op.getarglist())[0][0]
        arraydescr = op.getdescr()
        lendescr = arraydescr.lendescr

        ofs = lendescr.offset
        index = self.llvm.ConstInt(self.cpu.llvm_int_type, ofs, 1)
        index_array = self.rpython_array([index], self.llvm.ValueRef)
        array_type = self.llvm.PointerType(self.cpu.llvm_int_type, 0)

        # we need to pretend we're reading out of an array of ints
        # so llvm is happy with the GEP operand types
        cstring = CString("tmp_array_ptr")
        array_ptr = self.llvm.BuildPointerCast(self.builder,
                                               array, array_type,
                                               cstring.ptr)
        cstring = CString("length_field")
        ptr = self.llvm.BuildGEP(self.builder, self.cpu.llvm_int_type,
                                 array_ptr, index_array,
                                 1, cstring.ptr)
        cstring = CString("array_length")
        length = self.llvm.BuildLoad(self.builder,
                                     self.cpu.llvm_int_type,
                                     ptr, cstring.ptr)

        lltype.free(index_array, flavor='raw')
        self.ssa_vars[op] = length

    def parse_getarrayitem_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        array = args[0]
        index = args[1]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize
        lendescr_offset = arraydescr.lendescr.offset
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)

        value = llvm_array.get_elem(lendescr_offset+1, index)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize < 8:
                    cstring = CString("value_cast")
                    value = self.llvm.BuildFloatExt(self.builder, value,
                                                    self.cpu.llvm_float_type,
                                                    cstring.ptr)
            else:
                signed = 1 if arraydescr.is_item_signed() else 0
                cstring = CString("value_cast")
                value = self.llvm.BuildIntCast(self.builder, value,
                                               self.cpu.llvm_int_type,
                                               signed, cstring.ptr)

        self.ssa_vars[op] = value

    def parse_getarrayitem_raw(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        int_ptr = args[0]
        index = args[1]
        arraydescr = op.getdescr()

        cstring = CString("array_ptr")
        ptr = self.llvm.BuildIntToPtr(self.builder, int_ptr,
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        llvmarray = self.parse_array_descr_to_llvm(arraydescr, ptr)

        value = llvmarray.get_elem(index)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if arraydescr.itemsize < 8:
                    value = self.llvm.BuildFloatExt(self.builder, value,
                                                    self.cpu.llvm_float_type,
                                                    cstring.ptr)
            else:
                signed = 1 if arraydescr.is_item_signed() else 0
                value = self.llvm.BuildIntCast(self.builder, value,
                                               self.cpu.llvm_int_type,
                                               signed, cstring.ptr)

        self.ssa_vars[op] = value

    def parse_raw_load(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        int_ptr = args[0]
        index = args[1]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize

        # pretend raw array is array of i8 to compute proper address
        cstring = CString("ptr")
        array = self.llvm.BuildIntToPtr(self.builder, int_ptr,
                                        self.cpu.llvm_void_ptr, cstring.ptr)
        cstring = CString("index")
        index = self.llvm.BuildIntCast(self.builder, index,
                                       self.cpu.llvm_int_type,
                                       1, cstring.ptr)
        indecies = self.rpython_array([index], self.llvm.ValueRef)
        cstring = CString("array_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.cpu.llvm_char_type,
                                 array, indecies, 1, cstring.ptr)
        lltype.free(indecies, flavor='raw')

        # find the real type of the array and cast before loading
        elem_type, _ = self.get_array_elem_type(arraydescr, array, 1)
        elem_pointer_type = self.llvm.PointerType(elem_type, 0)
        cstring = CString("ptr_cast")
        ptr_cast = self.llvm.BuildPointerCast(self.builder, ptr,
                                              elem_pointer_type, cstring.ptr)
        cstring = CString("raw_load_res")
        value = self.llvm.BuildLoad(self.builder, elem_type,
                                    ptr_cast, cstring.ptr)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize < 8:
                    value = self.llvm.BuildFloatExt(self.builder, value,
                                                    self.cpu.llvm_float_type,
                                                    cstring.ptr)
            else:
                signed = 1 if arraydescr.is_item_signed() else 0
                value = self.llvm.BuildIntCast(self.builder, value,
                                               self.cpu.llvm_int_type,
                                               signed, cstring.ptr)

        self.ssa_vars[op] = value

    def parse_getinteriorfield_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        array = args[0]
        index = args[1]
        interiordescr = op.getdescr()
        arraydescr = interiordescr.get_arraydescr()
        lendescr_offset = arraydescr.lendescr.offset
        fielddescr = interiordescr.get_field_descr()
        field_index = fielddescr.index
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)

        print(llvm_array.depth)

        value = llvm_array.get_elem(lendescr_offset+1, index, field_index)

        if fielddescr.flag == 'S':
            target_type = self.cpu.llvm_int_type
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, target_type,
                                           1, cstring.ptr)
        elif fielddescr.flag == 'U':
            target_type = self.cpu.llvm_int_type
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, target_type,
                                           0, cstring.ptr)
        elif fielddescr.flag == 'F':
            if fielddescr.field_size < 8:
                cstring = CString("value_cast")
                value = self.llvm.BuildFloatExt(self.builder, value,
                                                self.cpu.llvm_float_type,
                                                cstring.ptr)

        self.ssa_vars[op] = value

    def parse_getfield_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        struct = args[0]
        fielddescr = op.getdescr()
        sizedescr = fielddescr.get_parent_descr()
        if sizedescr.get_vtable() != 0: index = fielddescr.index+1; plain=False
        else: index = fielddescr.index; plain=True
        llvm_struct = self.parse_struct_descr_to_llvm(sizedescr, struct,
                                                      plain=plain)
        value = llvm_struct.get_elem(index)

        if fielddescr.flag == 'S':
            target_type = self.cpu.llvm_int_type
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, target_type,
                                           1, cstring.ptr)
        elif fielddescr.flag == 'U':
            target_type = self.cpu.llvm_int_type
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, target_type,
                                           0, cstring.ptr)
        elif fielddescr.flag == 'F':
            if fielddescr.field_size < 8:
                cstring = CString("value_cast")
                value = self.llvm.BuildFloatExt(self.builder, value,
                                                self.cpu.llvm_float_type,
                                                cstring.ptr)

        self.ssa_vars[op] = value

    def parse_gc_load(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        ptr_int = args[0]
        offset = args[1]
        byte_size = args[2]

        if byte_size < 0: byte_size *= -1 #llvm doesn't care about signed/unsigned

        if ret == 'i': ret_type = self.llvm.IntType(self.cpu.context, byte_size)
        elif ret == 'f':
            if byte_size == 8:
                ret_type = self.cpu.llvm_float_type
            elif byte_size == 4:
                ret_type = self.cpu.llvm_single_float_type
            else:
                print("unknown float size")
                assert False
        elif ret == 'r': ret_type = self.cpu.llvm_void_ptr

        ptr_int += offset

        cstring = CString("gc_load_ptr")
        ptr = self.llvm.BuildIntToPtr(self.builder,
                                      self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                         ptr_int, 0),
                                      self.cpu.llvm_void_ptr, cstring.ptr)
        cstring = CString("gc_load_res")
        self.ssa_vars[op] = self.llvm.BuildLoad(self.builder, ret_type,
                                                ptr, cstring.ptr)

    def parse_new(self, op):
        sizedescr = op.getdescr()

        size = self.llvm.ConstInt(self.cpu.llvm_int_type, sizedescr.size, 0)
        args = self.rpython_array([size], self.llvm.ValueRef)
        cstring = CString("new_res")
        struct = self.llvm.BuildCall(self.builder, self.malloc, args, 1,
                                     cstring.ptr)
        self.llvm.add_deref_ret_attribute(struct, sizedescr.size)
        lltype.free(args, flavor='raw')

        llvm_struct = self.parse_struct_descr_to_llvm(sizedescr, struct, plain=True)

        self.ssa_vars[op] = llvm_struct.struct

    def parse_new_with_vtable(self, op):
        sizedescr = op.getdescr()

        size = self.llvm.ConstInt(self.cpu.llvm_int_type, sizedescr.size, 0)
        args = self.rpython_array([size], self.llvm.ValueRef)
        cstring = CString("new_res")
        struct = self.llvm.BuildCall(self.builder, self.malloc, args, 1,
                                     cstring.ptr)
        self.llvm.add_deref_ret_attribute(struct, sizedescr.size)
        lltype.free(args, flavor='raw')

        llvm_struct = self.parse_struct_descr_to_llvm(sizedescr, struct)

        if self.cpu.vtable_offset is not None:
            depth = llvm_struct.depth
            offset = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                        self.cpu.vtable_offset, 1)
            zero = self.llvm.ConstInt(self.cpu.llvm_indx_type, 0, 1)
            indices = ([zero] * depth) + [offset]
            indices = self.rpython_array(indices,
                                         self.llvm.ValueRef)
            cstring = CString("vtable_address")
            ptr = self.llvm.BuildGEP(self.builder, llvm_struct.struct_type,
                                     llvm_struct.struct, indices, depth+1,
                                     cstring.ptr)
            vtable_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                            sizedescr.get_vtable(), 0)
            cstring = CString("vtable")
            vtable = self.llvm.BuildIntToPtr(self.builder, vtable_int,
                                             self.cpu.llvm_void_ptr,
                                             cstring.ptr)
            self.llvm.BuildStore(self.builder, vtable, ptr)
            lltype.free(indices, flavor='raw')

        self.ssa_vars[op] = llvm_struct.struct

    def parse_new_array(self, op):
        num_elem = self.parse_args(op.getarglist())[0][0]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize
        basesize = arraydescr.basesize
        lendescr = arraydescr.lendescr

        itemsize_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, itemsize, 0)
        basesize_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, basesize, 0)
        cstring = CString("size")
        size_1 = self.llvm.BuildMul(self.builder, itemsize_llvm, num_elem,
                                    cstring.ptr)
        size = self.llvm.BuildAdd(self.builder, size_1, basesize_llvm,
                                  cstring.ptr)
        args = self.rpython_array([size], self.llvm.ValueRef)
        cstring = CString("new_res")
        array = self.llvm.BuildCall(self.builder, self.malloc, args, 1,
                                     cstring.ptr)
        # we won't know the full size until runtime but at least one elem
        # will be dereferenceable, and that provides other information too
        self.llvm.add_deref_ret_attribute(array, itemsize+basesize)
        lltype.free(args, flavor='raw')

        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)

        if lendescr is not None:
            offset = lendescr.offset
            offset_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, offset, 0)
            llvm_array.set_elem(num_elem, offset_llvm)

        self.ssa_vars[op] = llvm_array.struct # pascal array of length, array

    def parse_newstr(self, op):
        pass

    def parse_newunicode(self, op):
        pass

    def parse_force_token(self, op, c):
        self.forced = True
        force_descr = None
        failargs = None
        for next_op in self.operations[c:]:
            if (next_op.opnum == rop.GUARD_NOT_FORCED or
                next_op.opnum == rop.GUARD_NOT_FORCED_2):
                force_descr = next_op.getdescr()
                failargs = next_op.getfailargs()
                break
        if not force_descr or not failargs:
            raise Exception("Guard not force op not found")

        num_failargs = len(failargs)
        llvm_failargs = []
        for c, arg in enumerate(failargs):
            try:
                value = self.uncast(arg, self.ssa_vars[arg])
                llvm_failargs.append(value)
            except KeyError: # is either hole or hasn't been computed yet
                llvm_failargs.append(self.zero)

        self.cpu.descr_tokens[self.cpu.descr_token_cnt] = force_descr
        force_descr = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                         self.cpu.descr_token_cnt, 0)
        self.jitframe.set_elem(force_descr, 2)
        self.cpu.force_tokens[self.cpu.descr_token_cnt] = num_failargs
        self.cpu.descr_token_cnt += 1

        size = self.cpu.WORD+(num_failargs*self.cpu.WORD)
        size_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, size, 0)
        args = self.rpython_array([size_llvm], self.llvm.ValueRef)
        cstring = CString("ptr")
        struct = self.llvm.BuildCall(self.builder, self.malloc, args, 1,
                                     cstring.ptr)
        self.llvm.add_deref_ret_attribute(struct, size)
        lltype.free(args, flavor='raw')

        int_types = [self.cpu.llvm_int_type] * (num_failargs)
        jitframe_ptr_type = self.llvm.PointerType(self.jitframe.struct_type, 0)
        subtypes = [jitframe_ptr_type] + int_types
        subtype_array = self.rpython_array(subtypes, self.llvm.TypeRef)
        ForceTokenType = self.llvm.StructType(self.cpu.context,
                                              subtype_array,
                                              num_failargs+1, 0)
        lltype.free(subtype_array, flavor='raw')
        ptr_type = self.llvm.PointerType(ForceTokenType, 0)
        cstring = CString("force_token")
        struct = self.llvm.BuildPointerCast(self.builder, struct,
                                            ptr_type, cstring.ptr)
        force_token = LLVMStruct(self, subtypes, 1, struct = struct,
                                 struct_type = ForceTokenType)

        force_token.set_elem(self.jitframe.struct, 0)
        for i in range(num_failargs):
            force_token.set_elem(llvm_failargs[i], i+1)

        self.ssa_vars[op] = force_token.struct

    def parse_strhash(self, op):
        pass

    def parse_unicodehash(self, op):
        pass

    def parse_setarrayitem_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        array = args[0]
        index = args[1]
        value = args[2]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize
        lendescr_offset = arraydescr.lendescr.offset
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize == 4:
                    float_type = self.cpu.llvm_single_float_type
                    cstring = CString("value_cast")
                    value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                      float_type, cstring.ptr)
                elif itemsize != 8:
                    raise Exception("Unknown float size")
            elif itemsize != 64:
                int_type = self.llvm.IntType(self.cpu.context,
                                             itemsize*self.cpu.WORD)
                signed = 1 if arraydescr.is_item_signed() else 0
                cstring = CString("value_cast")
                value = self.llvm.BuildIntCast(self.builder, value, int_type,
                                               signed, cstring.ptr)

        llvm_array.set_elem(value, lendescr_offset+1, index)
        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize == 4:
                    float_type = self.cpu.llvm_single_float_type
                    cstring = CString("value_cast")
                    value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                      float_type, cstring.ptr)
                elif itemsize != 8:
                    raise Exception("Unknown float size")
            elif itemsize != 64:
                int_type = self.llvm.IntType(self.cpu.context,
                                             itemsize*self.cpu.WORD)
                signed = 1 if arraydescr.is_item_signed() else 0
                cstring = CString("value_cast")
                value = self.llvm.BuildIntCast(self.builder, value, int_type,
                                               signed, cstring.ptr)

    def parse_setarrayitem_raw(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        int_ptr = args[0]
        index = args[1]
        value = args[2]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize

        cstring = CString("array_ptr")
        ptr = self.llvm.BuildIntToPtr(self.builder, int_ptr,
                                      self.cpu.llvm_void_ptr,
                                      cstring.ptr)
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, ptr)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize == 4:
                    float_type = self.cpu.llvm_single_float_type
                    cstring = CString("value_cast")
                    value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                      float_type, cstring.ptr)
                elif itemsize != 8:
                    raise Exception("Unknown float size")
            elif itemsize != 64:
                int_type = self.llvm.IntType(self.cpu.context,
                                             itemsize*self.cpu.WORD)
                signed = 1 if arraydescr.is_item_signed() else 0
                cstring = CString("value_cast")
                value = self.llvm.BuildIntCast(self.builder, value, int_type,
                                               signed, cstring.ptr)

        value = llvm_array.set_elem(value, index)

    def parse_raw_store(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        int_ptr = args[0]
        index = args[1]
        value = args[2]
        arraydescr = op.getdescr()
        itemsize = arraydescr.itemsize

        # pretend raw array is array of i8 to compute proper address
        cstring = CString("ptr")
        array = self.llvm.BuildIntToPtr(self.builder, int_ptr,
                                        self.cpu.llvm_void_ptr, cstring.ptr)
        cstring = CString("index")
        index = self.llvm.BuildIntCast(self.builder, index,
                                       self.cpu.llvm_int_type,
                                       1, cstring.ptr)
        indecies = self.rpython_array([index], self.llvm.ValueRef)
        cstring = CString("array_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.cpu.llvm_char_type,
                                 array, indecies, 1, cstring.ptr)
        lltype.free(args, flavor='raw')

        # find the real type of the array and cast before loading
        elem_type, _ = self.get_array_elem_type(arraydescr, array, 1)
        elem_pointer_type = self.llvm.PointerType(elem_type, 0)
        cstring = CString("ptr_cast")
        ptr_cast = self.llvm.BuildPointerCast(self.builder, ptr,
                                              elem_pointer_type, cstring.ptr)

        if arraydescr.is_array_of_primitives():
            if arraydescr.is_array_of_floats():
                if itemsize == 4:
                    float_type = self.cpu.llvm_single_float_type
                    cstring = CString("value_cast")
                    value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                      float_type, cstring.ptr)
                elif itemsize != 8:
                    raise Exception("Unknown float size")
            elif itemsize != 64:
                int_type = self.llvm.IntType(self.cpu.context,
                                             itemsize*self.cpu.WORD)
                signed = 1 if arraydescr.is_item_signed() else 0
                cstring = CString("value_cast")
                value = self.llvm.BuildIntCast(self.builder, value, int_type,
                                               signed, cstring.ptr)

        self.llvm.BuildStore(self.builder, value, ptr_cast)

    def parse_setinteriorfield_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        array = args[0]
        index = args[1]
        value = args[2]
        interiordescr = op.getdescr()
        arraydescr = interiordescr.get_arraydescr()
        lendescr_offset = arraydescr.lendescr.offset
        fielddescr = interiordescr.get_field_descr()
        field_index = fielddescr.index
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)

        if fielddescr.flag == 'S':
            field_type = self.llvm.IntType(self.cpu.context,
                                           fielddescr.field_size*self.cpu.WORD)
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, field_type,
                                           1, cstring.ptr)
        elif fielddescr.flag == 'U':
            field_type = self.llvm.IntType(self.cpu.context,
                                           fielddescr.field_size*self.cpu.WORD)
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, field_type,
                                           0, cstring.ptr)
        elif fielddescr.flag == 'F':
            if fielddescr.field_size == 4:
                cstring = CString("value_cast")
                value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                  self.cpu.llvm_single_float_type,
                                                  cstring.ptr)
            elif fielddescr.field_size != 8:
                raise Exception("Unknown float size")

        llvm_array.set_elem(value, lendescr_offset+1, index, field_index)


    def parse_setfield_gc(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        struct = args[0]
        value = args[1]
        fielddescr = op.getdescr()
        sizedescr = fielddescr.get_parent_descr()
        if sizedescr.get_vtable() != 0: index = fielddescr.index+1; plain=False
        else: index = fielddescr.index; plain=True
        llvm_struct = self.parse_struct_descr_to_llvm(sizedescr, struct,
                                                      plain=plain)

        if fielddescr.flag == 'S':
            field_type = llvm_struct.subtypes[index]
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, field_type,
                                           1, cstring.ptr)
        elif fielddescr.flag == 'U':
            field_type = llvm_struct.subtypes[index]
            cstring = CString("value_cast")
            value = self.llvm.BuildIntCast(self.builder, value, field_type,
                                           0, cstring.ptr)
        elif fielddescr.flag == 'F':
            if fielddescr.field_size == 4:
                cstring = CString("value_cast")
                value = self.llvm.BuildFloatTrunc(self.builder, value,
                                                  self.cpu.llvm_single_float_type,
                                                  cstring.ptr)
            elif fielddescr.field_size != 8:
                raise Exception("Unknown float size")

        llvm_struct.set_elem(value, index)

    def parse_zero_array(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        array = args[0]
        index = args[1]
        length = args[2]
        arraydescr = op.getdescr()
        lendescr_offset = arraydescr.lendescr.offset
        llvm_array = self.parse_array_descr_to_llvm(arraydescr, array)
        itemsize = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                      arraydescr.itemsize, 0)

        cstring = CString("index")
        index = self.llvm.BuildUDiv(self.builder, index, itemsize, cstring.ptr)
        dst = llvm_array.get_ptr(lendescr_offset+1, index)
        cstring = CString("dst")
        dst = self.llvm.BuildPointerCast(self.builder, dst,
                                         self.cpu.llvm_void_ptr, cstring.ptr)
        zero = self.llvm.ConstInt(self.cpu.llvm_char_type, 0, 0)
        args = self.rpython_array([dst, zero, length, self.false], self.llvm.ValueRef)
        cstring = CString("")
        self.llvm.BuildCall(self.builder, self.memset_intrinsic, args, 4,
                            cstring.ptr)
        lltype.free(args, flavor='raw')

    def get_arg_types(self, call_descr, params):
        arg_types = []
        for c, typ in enumerate(call_descr.arg_classes):
            if typ == 'i':
                arg_type = call_descr.arg_types[c]
                if type(arg_type) is int:
                    int_type = self.llvm.IntType(self.cpu.context,
                                                 arg_type*self.cpu.WORD)
                    arg_types.append(int_type)
                    cstring = CString("arg_cast")
                    params[c] = self.llvm.BuildIntCast(self.builder, params[c],
                                                       int_type, 1, cstring.ptr)
                elif arg_type is lltype.Signed or lltype.Unsigned:
                    arg_types.append(self.cpu.llvm_int_type)
                elif arg_type is rffi.INT:
                    llvm_type = self.cpu.llvm_indx_type #indx_type = 32bits
                    arg_types.append(llvm_type)
                    cstring = CString("arg_cast")
                    params[c] = self.llvm.BuildIntCast(self.builder, params[c],
                                                       llvm_type, 1, cstring.ptr)
                elif arg_type is rffi.SHORT:
                    llvm_type = self.cpu.llvm_short_type
                    arg_types.append(llvm_type)
                    cstring = CString("arg_cast")
                    params[c] = self.llvm.BuildIntCast(self.builder, params[c],
                                                       llvm_type, 1, cstring.ptr)
                elif arg_type is rffi.CHAR:
                    llvm_type = self.cpu.llvm_char_type
                    arg_types.append(llvm_type)
                    cstring = CString("arg_cast")
                    params[c] = self.llvm.BuildIntCast(self.builder, params[c],
                                                       llvm_type, 1, cstring.ptr)
                else: raise Exception("Unknown int arg type: "+str(arg_type))
            elif typ == 'f' or typ == 'L': arg_types.append(self.cpu.llvm_float_type)
            elif typ == 'r':
                cstring = CString("cast_ptr")
                params[c] = self.llvm.BuildPointerCast(self.builder, params[c],
                                                       self.cpu.llvm_void_ptr,
                                                       cstring.ptr)
                arg_types.append(self.cpu.llvm_void_ptr)
            elif typ == 'S': arg_types.append(self.cpu.llvm_single_float_type)
            else: raise Exception("Unknown arg type")
        return arg_types

    def parse_save_exception(self, op):
        ptr_ptr_type = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        exception_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                self.cpu.pos_exc_value(), 0)
        cstring = CString("exception_addr")
        exception_addr = self.llvm.BuildIntToPtr(self.builder, exception_addr_int,
                                                 ptr_ptr_type, cstring.ptr)
        cstring = CString("exception")
        exception = self.llvm.BuildLoad(self.builder, self.cpu.llvm_void_ptr,
                                        exception_addr, cstring.ptr)

        cstring = CString("null_ptr")
        null_ptr = self.llvm.BuildIntToPtr(self.builder, self.zero,
                                           self.cpu.llvm_void_ptr,
                                           cstring.ptr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_addr)

        self.ssa_vars[op] = exception

    def parse_save_exc_class(self, op):
        ptr_ptr_type = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        exception_vtable_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                       self.cpu.pos_exception(),
                                                       0)
        cstring = CString("exception_vtable_addr")
        exception_vtable_addr = self.llvm.BuildIntToPtr(self.builder,
                                                        exception_vtable_addr_int,
                                                        ptr_ptr_type, cstring.ptr)
        cstring = CString("exception_vtable_ptr")
        exception_vtable_ptr = self.llvm.BuildLoad(self.builder,
                                                   self.cpu.llvm_void_ptr,
                                                   exception_vtable_addr,
                                                   cstring.ptr)
        cstring = CString("exception_vtable")
        exception_vtable = self.llvm.BuildPtrToInt(self.builder,
                                                   exception_vtable_ptr,
                                                   self.cpu.llvm_int_type,
                                                   cstring.ptr)

        cstring = CString("null_ptr")
        null_ptr = self.llvm.BuildIntToPtr(self.builder, self.zero,
                                           self.cpu.llvm_void_ptr,
                                           cstring.ptr)
        self.llvm.BuildStore(self.builder, null_ptr, exception_vtable_addr)

        self.ssa_vars[op] = exception_vtable

    def parse_restore_exception(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        vtable = args[0]
        exception = args[1]
        ptr_ptr_type = self.llvm.PointerType(self.cpu.llvm_void_ptr, 0)
        cstring = CString("vtable")
        vtable = self.llvm.BuildIntToPtr(self.builder, vtable,
                                         self.cpu.llvm_void_ptr,
                                         cstring.ptr)

        exception_vtable_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                       self.cpu.pos_exception(),
                                                       0)
        cstring = CString("exception_vtable_addr")
        exception_vtable_addr = self.llvm.BuildIntToPtr(self.builder,
                                                        exception_vtable_addr_int,
                                                        ptr_ptr_type, cstring.ptr)
        exception_addr_int = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                self.cpu.pos_exc_value(), 0)
        cstring = CString("exception_addr")
        exception_addr = self.llvm.BuildIntToPtr(self.builder, exception_addr_int,
                                                 ptr_ptr_type, cstring.ptr)

        self.llvm.BuildStore(self.builder, vtable, exception_vtable_addr)
        self.llvm.BuildStore(self.builder, exception, exception_addr)

    def parse_call(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        func_int_ptr = args[0]
        params = args[1:]
        call_descr = op.getdescr()
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr
        elif ret == 'f': ret_type = self.cpu.llvm_float_type
        elif ret == 'n': ret_type = self.cpu.llvm_void_type
        elif ret == 'i': ret_type = self.llvm.IntType(self.cpu.context,
                                                      self.cpu.WORD*call_descr.
                                                      result_size)
        arg_types = self.get_arg_types(call_descr, params)

        if ret != 'n':
            res = self.call_function(func_int_ptr, ret_type,
                                     arg_types, params,
                                     "call_res")
            if ret == 'i' and call_descr.result_size < 8:
                signed = 1 if call_descr.result_flag == 'S' else 0
                cstring = CString("res_cast")
                res = self.llvm.BuildIntCast(self.builder, res,
                                             self.cpu.llvm_int_type, signed,
                                             cstring.ptr)
            if ret == 'f' and call_descr.result_size == 4:
                cstring = CString("res_cast")
                res = self.llvm.FloatExt(self.builder, res,
                                         self.cpu.llvm_float_type,
                                         cstring.ptr)
            self.ssa_vars[op] = res
        else:
            self.call_function(func_int_ptr, ret_type,
                                arg_types, params, "")

    def parse_cond_call(self, op, c):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cnd = args[0]
        func_int_ptr = args[1]
        params = args[2:]
        call_descr = op.getdescr()
        arg_types = self.get_arg_types(call_descr, params)
        ret_type = self.cpu.llvm_void_type

        next_op = self.operations[c+1]
        if next_op.opnum in (rop.GUARD_NO_EXCEPTION, rop.GUARD_EXCEPTION):
            self.guard_follows = True
            resume, bailout = self.guard_handler.setup_guard(next_op)
        else:
            cstring = CString("resume")
            resume = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)

        cstring = CString("cnd")
        cnd = self.llvm.BuildIntCast(self.builder, cnd, self.cpu.llvm_int_type,
                                     0, cstring.ptr)
        cstring = CString("cond_call_cmp")
        cmp = self.llvm.BuildICmp(self.builder, self.intne, cnd, self.zero,
                                  cstring.ptr)
        cstring = CString("call_block")
        call_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)

        branch = self.llvm.BuildCondBr(self.builder, cmp, call_block,
                                       resume)

        # set branch weights to assume we will rarely call the function
        self.set_branch_weights(branch, "cond_call_weights", 10, 90)

        self.llvm.PositionBuilderAtEnd(self.builder, call_block)
        self.call_function(func_int_ptr, ret_type, arg_types, params, "")
        if not self.guard_follows:
            self.llvm.BuildBr(self.builder, resume)

        if self.guard_follows:
            if next_op.opnum == rop.GUARD_NO_EXCEPTION:
                self.parse_guard_no_exception(next_op, resume, bailout)
            elif next_op.opnum == rop.GUARD_EXCEPTION:
                self.parse_guard_exception(next_op, resume, bailout)
        else:
            self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_cond_call_value(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cnd = args[0]
        func_int_ptr = args[1]
        params = args[2:]
        call_descr = op.getdescr()
        arg_types = self.get_arg_types(call_descr, params)
        if ret == 'i': ret_type = self.cpu.llvm_int_type
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr

        cstring = CString("cmp")
        cmp = self.llvm.BuildIsNull(self.builder, cnd, cstring.ptr)

        cstring = CString("call_block")
        call_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)
        cstring = CString("resume_block")
        resume_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                  cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cmp, call_block, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, call_block)
        call_res = self.call_function(func_int_ptr, ret_type, arg_types, params,
                                      "call_res")
        if ret == 'i' and call_descr.result_size < 8:
            signed = 1 if call_descr.result_flag == 'S' else 0
            cstring = CString("res_cast")
            call_res = self.llvm.BuildIntCast(self.builder, call_res,
                                              self.cpu.llvm_int_type, signed,
                                              cstring.ptr)
        self.llvm.BuildBr(self.builder, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, resume_block)
        phi_type = ret_type
        cstring = CString("cond_phi")
        phi = self.llvm.BuildPhi(self.builder, phi_type, cstring.ptr)
        self.llvm.AddIncoming(phi, call_res, call_block)
        self.llvm.AddIncoming(phi, cnd, self.entry)
        self.ssa_vars[op] = phi

    # FIXME: won't work currently as backend's resource management can not
    # hold two traces at once in memory
    def parse_call_assembler(self, op, ret):
        params = [arg for arg, _ in self.parse_args(op.getarglist())]
        looptoken = op.getdescr()
        func_int_ptr = looptoken._ll_function_addr
        func_int_ptr = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                          func_int_ptr, 0)
        call_descr = looptoken.outermost_jitdriver_sd.portal_calldescr
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr
        elif ret == 'f': ret_type = self.cpu.llvm_float_type
        elif ret == 'n': ret_type = self.cpu.llvm_void_type
        elif ret == 'i': ret_type = self.llvm.IntType(self.cpu.context,
                                                      self.cpu.WORD*call_descr.
                                                      result_size)
        arg_types = self.get_arg_types(call_descr, params)

        if ret != 'n':
            res = self.call_function(func_int_ptr, ret_type,
                                                   arg_types, params,
                                                   "call_res")
            self.ssa_vars[op] = res
        else:
            res = self.call_function(func_int_ptr, ret_type,
                               arg_types, params, "")

    def parse_call_release_gil(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        errno = args[0]
        func_int_ptr = args[1]
        params = args[2:]
        call_descr = op.getdescr()
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr
        elif ret == 'f': ret_type = self.cpu.llvm_float_type
        elif ret == 'n': ret_type = self.cpu.llvm_void_type
        elif ret == 'i': ret_type = self.llvm.IntType(self.cpu.context,
                                                      self.cpu.WORD*call_descr.
                                                      result_size)
        arg_types = self.get_arg_types(call_descr, params)

        if ret != 'n':
            res = self.call_function(func_int_ptr, ret_type,
                                     arg_types, params,
                                     "call_res")
            if ret == 'i' and call_descr.result_size < 8:
                signed = 1 if call_descr.result_flag == 'S' else 0
                cstring = CString("res_cast")
                res = self.llvm.BuildIntCast(self.builder, res,
                                             self.cpu.llvm_int_type, signed,
                                             cstring.ptr)
            if ret == 'f' and call_descr.result_size == 4:
                cstring = CString("res_cast")
                res = self.llvm.FloatExt(self.builder, res,
                                         self.cpu.llvm_float_type,
                                         cstring.ptr)

            self.ssa_vars[op] = res
        else:
            self.call_function(func_int_ptr, ret_type,
                                arg_types, params, "")

    def parse_int_ovf(self, op, binop):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]

        cstring = CString("lhs_wide")
        lhs_wide = self.llvm.BuildSExt(self.builder, lhs,
                                       self.cpu.llvm_wide_int, cstring.ptr)
        cstring = CString("rhs_wide")
        rhs_wide = self.llvm.BuildSExt(self.builder, rhs,
                                       self.cpu.llvm_wide_int, cstring.ptr)

        if binop == "+":
            cstring = CString("overflow_add")
            res = self.llvm.BuildAdd(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)
        elif binop == "-":
            cstring = CString("overflow_sub")
            res = self.llvm.BuildSub(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)
        elif binop == "*":
            cstring = CString("overflow_mul")
            res = self.llvm.BuildMul(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)

        cstring = CString("max_flag")
        max_flag = self.llvm.BuildICmp(self.builder, self.intsgt, res,
                                       self.max_int, cstring.ptr)
        cstring = CString("min_flag")
        min_flag = self.llvm.BuildICmp(self.builder, self.intslt, res,
                                       self.min_int, cstring.ptr)

        cstring = CString("overflow_check")
        check = self.llvm.BuildOr(self.builder, max_flag, min_flag, cstring.ptr)
        self.llvm.BuildStore(self.builder, check, self.overflow)

        cstring = CString("int_add_ovf_res")
        self.ssa_vars[op] = self.llvm.BuildTrunc(self.builder, res,
                                                 self.cpu.llvm_int_type,
                                                 cstring.ptr)

class LLVMArray:
    def __init__(self, dispatcher, elem_type, depth, elem_counts=None,
                 caller_block=None, array=None, array_type=None):
        self.dispatcher = dispatcher
        self.builder = self.dispatcher.builder
        self.cpu = self.dispatcher.cpu
        self.llvm = self.dispatcher.llvm
        self.elem_type = elem_type
        self.elem_counts = elem_counts
        self.depth = depth
        indecies = rffi.CArray(self.llvm.ValueRef)
        self.indecies_array = lltype.malloc(indecies, n=self.depth+1,
                                            flavor='raw')
        index = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 1)
        self.indecies_array[0] = index #held array is actually a pointer to the array, will always needs to be deref'ed at indx 0 first

        if array_type is None:
            self.array_type = self.get_array_type()
        else:
            self.array_type = array_type
        if array is None:
            self.array = self.allocate_array(dispatcher.entry, caller_block)
        else:
            self.array = array

    def change_object(self, ptr):
        self.array = ptr

    def get_array_type(self):
        base_type_count = self.elem_counts[-1]
        array_type = self.llvm.ArrayType(self.elem_type,
                                         base_type_count)
        for count in self.elem_counts[:-1]:
            array_type = self.llvm.ArrayType(array_type, count)
        return array_type

    def allocate_array(self, entry, caller_block):
        """
        Allocas should be placed at the entry block of a function to aid
        LLVM's optimiser
        """
        instr = self.llvm.GetFirstInstruction(entry)
        self.llvm.PositionBuilderBefore(self.builder, instr)
        index = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                   0, 1)
        self.indecies_array[0] = index #held array is actually a pointer to the array, will always needs to be deref'ed at indx 0 first
        cstring = CString("array")
        array = self.llvm.BuildAlloca(self.builder, self.array_type,
                                      cstring.ptr) #TODO: check for stack overflow
        self.llvm.PositionBuilderAtEnd(self.builder, caller_block)
        self.dispatcher.local_vars_size += self.llvm.SizeOf(self.array_type)
        return array

    def get_elem(self, *indecies):
        """
        Note that LLVM will regalloc a whole aggregate type you ask it to.
        Use get_ptr if you only want the address, and not the load.
        """
        ptr = self.get_ptr(*indecies)
        elem_type = self.llvm.getResultElementType(ptr)
        cstring = CString("array_elem")
        elem = self.llvm.BuildLoad(self.builder, elem_type,
                                   ptr, cstring.ptr)
        return elem

    def set_elem(self, elem, *indecies):
        ptr = self.get_ptr(*indecies)
        self.llvm.BuildStore(self.builder, elem, ptr)

    def get_ptr(self, *indecies):
        for i in range(len(indecies)):
            index = indecies[i]
            if type(index) is int:
                index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                           index, 1)
            else:
                cstring = CString("index")
                index = self.llvm.BuildIntCast(self.builder, index,
                                               self.cpu.llvm_int_type,
                                               1, cstring.ptr)
            self.indecies_array[i+1] = index

        cstring = CString("array_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.array_type,
                                 self.array, self.indecies_array,
                                 len(indecies)+1, cstring.ptr)
        return ptr

    def __del__(self):
        lltype.free(self.indecies_array, flavor='raw')

class LLVMStruct:
    def __init__(self, dispatcher, subtypes, depth, caller_block=None,
                 struct=None, struct_type=None):
        self.dispatcher = dispatcher
        self.builder = self.dispatcher.builder
        self.cpu = self.dispatcher.cpu
        self.llvm = self.dispatcher.llvm
        self.subtypes = subtypes #only defined up to depth=1
        self.elem_count = len(subtypes)
        self.depth = depth
        indecies = rffi.CArray(self.llvm.ValueRef)
        self.indecies_array = lltype.malloc(indecies, n=self.depth+1,
                                            flavor='raw')
        index = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 1)
        self.indecies_array[0] = index #held struct is actually a pointer to the array, will always needs to be deref'ed at indx 0 first
        if struct_type is None:
            self.struct_type = dispatcher.get_struct_from_subtypes(subtypes)
        else:
            self.struct_type = struct_type
        if struct is None:
            self.struct = self.allocate_struct(dispatcher.entry, caller_block)
        else:
            self.struct = struct

    def change_object(self, ptr):
        self.struct = ptr

    def allocate_struct(self, entry, caller_block):
        """
        Allocas should be placed at the entry block of a function to aid
        LLVM's optimiser
        """
        instr = self.llvm.GetFirstInstruction(entry)
        self.llvm.PositionBuilderBefore(self.builder, instr)
        cstring = CString("struct")
        struct = self.llvm.BuildAlloca(self.builder, self.struct_type,
                                      cstring.ptr) #TODO: check for stack overflow
        self.llvm.PositionBuilderAtEnd(self.builder, caller_block)
        self.dispatcher.local_vars_size += self.llvm.SizeOf(self.struct_type)
        return struct

    def get_elem(self, *indecies):
        """
        Note that LLVM will regalloc a whole aggregate type you ask it to.
        Use get_ptr if you only want the address, and not the load.
        """
        ptr = self.get_ptr(*indecies)
        elem_type = self.llvm.getResultElementType(ptr)
        cstring = CString("struct_elem")
        elem = self.llvm.BuildLoad(self.builder, elem_type, ptr,
                                   cstring.ptr)
        return elem

    def set_elem(self, elem, *indecies):
        ptr = self.get_ptr(*indecies)
        self.llvm.BuildStore(self.builder, elem, ptr)

    def get_ptr(self, *indecies):
        for i in range(len(indecies)):
            index = indecies[i]
            cstring = CString("index")
            if type(index) is int:
                index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                           indecies[i], 1)
            else:
                index = self.llvm.BuildIntCast(self.builder, index,
                                               self.cpu.llvm_indx_type, 1,
                                               cstring.ptr)
            self.indecies_array[i+1] = index
        cstring = CString("struct_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.struct_type,
                                 self.struct, self.indecies_array,
                                 len(indecies)+1, cstring.ptr)
        return ptr

    def __del__(self):
        lltype.free(self.indecies_array, flavor='raw')
