
from pypy.jit.backend.llvm.llvm_rffi import *


def test_from_llvm_py_example_1():
    # NOTE: minimal GC (some objects are never freed)

    # Create an (empty) module.
    my_module = LLVMModuleCreateWithName("my_module")

    # All the types involved here are "int"s. This type is represented
    # by an object of type LLVMTypeRef:
    ty_int = LLVMInt32Type()

    # We need to represent the class of functions that accept two integers
    # and return an integer. This is represented by another LLVMTypeRef:
    arglist = lltype.malloc(rffi.CArray(LLVMTypeRef), 2, flavor='raw')
    arglist[0] = ty_int
    arglist[1] = ty_int
    ty_func = LLVMFunctionType(ty_int, arglist, 2, False)
    lltype.free(arglist, flavor='raw')

    # Now we need a function named 'sum' of this type. Functions are not
    # free-standing; it needs to be contained in a module.
    f_sum = LLVMAddFunction(my_module, "sum", ty_func)
    f_arg_0 = LLVMGetParam(f_sum, 0)
    f_arg_1 = LLVMGetParam(f_sum, 1)

    # Our function needs a "basic block" -- a set of instructions that
    # end with a terminator (like return, branch etc.). By convention
    # the first block is called "entry".
    bb = LLVMAppendBasicBlock(f_sum, "entry")

    # Let's add instructions into the block. For this, we need an
    # instruction builder:
    builder = LLVMCreateBuilder()
    LLVMPositionBuilderAtEnd(builder, bb)

    # OK, now for the instructions themselves. We'll create an add
    # instruction that returns the sum as a value, which we'll use
    # a ret instruction to return.
    tmp = LLVMBuildAdd(builder, f_arg_0, f_arg_1, "tmp")
    LLVMBuildRet(builder, tmp)
    LLVMDisposeBuilder(builder)

    # We've completed the definition now! Let's see the LLVM assembly
    # language representation of what we've created: (it goes to stderr)
    LLVMDumpModule(my_module)
    return locals()


class LLVMException(Exception):
    pass


def create_execution_engine(my_module):
    teardown_now()
    # Create a module provider object first. Modules can come from
    # in-memory IRs like what we created now, or from bitcode (.bc)
    # files. The module provider abstracts this detail.
    mp = LLVMCreateModuleProviderForExistingModule(my_module)

    # Create an execution engine object. This creates a JIT compiler,
    # or complain on platforms that don't support it.
    ee_out = lltype.malloc(rffi.CArray(LLVMExecutionEngineRef), 1, flavor='raw')
    error_out = lltype.malloc(rffi.CArray(rffi.CCHARP), 1, flavor='raw')
    error_out[0] = lltype.nullptr(rffi.CCHARP.TO)
    try:
        error = LLVMCreateJITCompiler(ee_out, mp, True, error_out)
        if rffi.cast(lltype.Signed, error) != 0:
            raise LLVMException(rffi.charp2str(error_out[0]))
        ee = ee_out[0]
    finally:
        if error_out[0]:
            LLVMDisposeMessage(error_out[0])
        lltype.free(error_out, flavor='raw')
        lltype.free(ee_out, flavor='raw')

    set_teardown_function(lambda: LLVMDisposeExecutionEngine(ee))
    return ee


def test_from_llvm_py_example_2():
    d = test_from_llvm_py_example_1()
    my_module = d['my_module']
    ty_int = d['ty_int']
    f_sum = d['f_sum']

    # Create an execution engine object. This creates a JIT compiler,
    # or complain on platforms that don't support it.
    ee = create_execution_engine(my_module)

    # The arguments needs to be passed as "GenericValue" objects.
    args = lltype.malloc(rffi.CArray(LLVMGenericValueRef), 2, flavor='raw')
    args[0] = LLVMCreateGenericValueOfInt(ty_int, 100, True)
    args[1] = LLVMCreateGenericValueOfInt(ty_int, 42, True)

    # Now let's compile and run!
    retval = LLVMRunFunction(ee, f_sum, 2, args)
    LLVMDisposeGenericValue(args[1])
    LLVMDisposeGenericValue(args[0])
    lltype.free(args, flavor='raw')

    # The return value is also GenericValue. Let's check it.
    ulonglong = LLVMGenericValueToInt(retval, True)
    LLVMDisposeGenericValue(retval)
    res = rffi.cast(lltype.Signed, ulonglong)
    assert res == 142


def test_from_llvm_py_example_3():
    """This test is the same as the previous one.  Just tests that we
    have freed enough stuff to be able to call it again."""
    test_from_llvm_py_example_2()


def test_add_ovf():
    my_module = LLVMModuleCreateWithName("my_module")
    ty_int = LLVMInt32Type()
    f_add_ovf = LLVM_Intrinsic_add_ovf(my_module, ty_int)
    #
    arglist = lltype.malloc(rffi.CArray(LLVMTypeRef), 2, flavor='raw')
    arglist[0] = ty_int
    arglist[1] = ty_int
    ty_func = LLVMFunctionType(ty_int, arglist, 2, False)
    lltype.free(arglist, flavor='raw')
    #
    f_sum_ovf = LLVMAddFunction(my_module, "sum_ovf", ty_func)
    f_arg_0 = LLVMGetParam(f_sum_ovf, 0)
    f_arg_1 = LLVMGetParam(f_sum_ovf, 1)
    #
    bb = LLVMAppendBasicBlock(f_sum_ovf, "entry")
    #
    builder = LLVMCreateBuilder()
    LLVMPositionBuilderAtEnd(builder, bb)
    #
    arglist = lltype.malloc(rffi.CArray(LLVMValueRef), 2, flavor='raw')
    arglist[0] = f_arg_0
    arglist[1] = f_arg_1
    tmp = LLVMBuildCall(builder, f_add_ovf, arglist, 2, "tmp")
    lltype.free(arglist, flavor='raw')
    #
    tmp0 = LLVMBuildExtractValue(builder, tmp, 0, "tmp0")
    tmp1 = LLVMBuildExtractValue(builder, tmp, 1, "tmp1")
    c666 = LLVMConstInt(ty_int, 666, 1)
    tmp2 = LLVMBuildSelect(builder, tmp1, c666, tmp0, "tmp2")
    #
    LLVMBuildRet(builder, tmp2)
    LLVMDisposeBuilder(builder)
    #
    LLVMDumpModule(my_module)

    ee = create_execution_engine(my_module)
    #
    OVERFLOW = 666
    for x, y, z in [(100, 42, 142),
                    (sys.maxint, 1, OVERFLOW),
                    (-10, -sys.maxint, OVERFLOW)]:
        args = lltype.malloc(rffi.CArray(LLVMGenericValueRef), 2, flavor='raw')
        args[0] = LLVMCreateGenericValueOfInt(ty_int, x, True)
        args[1] = LLVMCreateGenericValueOfInt(ty_int, y, True)
        retval = LLVMRunFunction(ee, f_sum_ovf, 2, args)
        LLVMDisposeGenericValue(args[1])
        LLVMDisposeGenericValue(args[0])
        lltype.free(args, flavor='raw')
        #
        ulonglong = LLVMGenericValueToInt(retval, True)
        LLVMDisposeGenericValue(retval)
        res = rffi.cast(lltype.Signed, ulonglong)
        assert res == z
