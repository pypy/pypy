import time

from pypy.translator.llvm import build_llvm_module
from pypy.translator.llvm.database import Database 
from pypy.translator.llvm.pyxwrapper import write_pyx_wrapper 
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm.codewriter import CodeWriter
from pypy.translator.llvm import extfuncnode
from pypy.translator.llvm.module.support import extdeclarations, extfunctions
from pypy.translator.llvm.node import LLVMNode
from pypy.translator.llvm.externs2ll import post_setup_externs, generate_llfile
from pypy.translator.llvm.gc import GcPolicy
from pypy.translator.llvm.exception import ExceptionPolicy
from pypy.translator.translator import Translator
from pypy.translator.llvm.log import log

# keep for propersity sake 
"""run_pypy-llvm.sh [aug 29th 2005]
before slotifying: 350Mb
after  slotifying: 300Mb, 35 minutes until the .ll file is fully written.
STATS (1, "<class 'pypy.translator.llvm.arraynode.VoidArrayTypeNode'>")
STATS (1, "<class 'pypy.translator.llvm.opaquenode.OpaqueTypeNode'>")
STATS (9, "<class 'pypy.translator.llvm.structnode.StructVarsizeTypeNode'>")
STATS (46, "<class 'pypy.translator.llvm.extfuncnode.ExternalFuncNode'>")
STATS (52, "<class 'pypy.translator.llvm.arraynode.ArrayTypeNode'>")
STATS (189, "<class 'pypy.translator.llvm.arraynode.VoidArrayNode'>")
STATS (819, "<class 'pypy.translator.llvm.opaquenode.OpaqueNode'>")
STATS (1250, "<class 'pypy.translator.llvm.funcnode.FuncTypeNode'>")
STATS (1753, "<class 'pypy.translator.llvm.structnode.StructTypeNode'>")
STATS (5896, "<class 'pypy.translator.llvm.funcnode.FuncNode'>")
STATS (24013, "<class 'pypy.translator.llvm.arraynode.ArrayNode'>")
STATS (25411, "<class 'pypy.translator.llvm.structnode.StructVarsizeNode'>")
STATS (26210, "<class 'pypy.translator.llvm.arraynode.StrArrayNode'>")
STATS (268884, "<class 'pypy.translator.llvm.structnode.StructNode'>")

init took 00m00s
setup_all took 08m14s
setup_all externs took 00m00s
generate_ll took 00m02s
write externs type declarations took 00m00s
write data type declarations took 00m02s
write global constants took 09m49s
write function prototypes took 00m00s
write declarations took 00m03s
write implementations took 01m54s
write support functions took 00m00s
write external functions took 00m00s
"""

class GenLLVM(object):

    # see open_file() below
    function_count = {}
    llexterns_header = llexterns_functions = None

    def __init__(self, translator, gcpolicy=None, exceptionpolicy=None,
                 debug=False, logging=True):
    
        # reset counters
        LLVMNode.nodename_count = {}    

        # create and set internals
        self.db = Database(self, translator)
        self.gcpolicy = gcpolicy
        self.translator = translator
        self.exceptionpolicy = exceptionpolicy

        # the debug flag is for creating comments of every operation
        # that may be executed
        self.debug = debug 

        # the logging flag is for logging information statistics in the build
        # process
        self.logging = logging

    def gen_llvm_source(self, func=None):

        self._checkpoint()

        # get entry point
        entry_point, func_name = self.get_entry_point(func)
        self._checkpoint('get_entry_point')

        # open file & create codewriter
        codewriter, filename = self.create_codewrite(func_name)
        self._checkpoint('open file and create codewriter')

        # set up all nodes
        self.db.setup_all()
        self.entrynode = self.db.set_entrynode(entry_point)
        self._checkpoint('setup_all first pass')

        # post set up nodes 
        extern_decls = post_setup_externs(self.db)
        self.translator.rtyper.specialize_more_blocks()
        self.db.setup_all()
        self._checkpoint('setup_all second pass')

        self._print_node_stats()

        # create ll file from c code 
        self.setup_externs(extern_decls)
        self._checkpoint('setup_externs')
    
        # write external function headers
        codewriter.header_comment('External Function Headers')
        codewriter.append(self.llexterns_header)

        codewriter.header_comment("Type Declarations")

        # write extern type declarations
        self.write_extern_decls(codewriter, extern_decls)
        self._checkpoint('write externs type declarations')

        # write node type declarations
        for typ_decl in self.db.getnodes():
            typ_decl.writedatatypedecl(codewriter)
        self._checkpoint('write data type declarations')

        codewriter.header_comment("Global Data")

        # write pbcs
        for typ_decl in self.db.getnodes():
            typ_decl.writeglobalconstants(codewriter)
        self._checkpoint('write global constants')

        codewriter.header_comment("Function Prototypes")

        # write external protos
        codewriter.append(extdeclarations)

        # write garbage collection protos
        codewriter.append(self.gcpolicy.declarations())

        # write node protos
        for typ_decl in self.db.getnodes():
            typ_decl.writedecl(codewriter)

        self._checkpoint('write function prototypes')

        codewriter.startimpl()

        codewriter.header_comment("Function Implementation")

        # write external function implementations
        codewriter.header_comment('External Function Implementation')
        codewriter.append(self.llexterns_functions)

        self._checkpoint('write external functions')

        # write exception implementaions
        codewriter.append(self.exceptionpolicy.llvmcode(self.entrynode))

        # write support implementations
        for key, (deps, impl) in extfunctions.items():
            print key
            if key in ["%main_noargs", "%main"]:
                continue
            codewriter.append(impl)
        self._checkpoint('write support implentations')

        # write all node implementations
        for typ_decl in self.db.getnodes():
            typ_decl.writeimpl(codewriter)
        self._checkpoint('write node implementations')

        # write entry point if there is one
        self.write_entry_point(codewriter)
        codewriter.comment("End of file")

        self._checkpoint('done')

        return filename
    
    def get_entry_point(self, func):
        if func is None:
            func = self.translator.entrypoint
        self.entrypoint = func

        ptr = getfunctionptr(self.translator, func)
        c = inputconst(lltype.typeOf(ptr), ptr)
        self.db.prepare_arg_value(c)
        return c.value._obj, func.func_name

    def setup_externs(self, extern_decls):
        # we cache the llexterns to make tests run faster
        if self.llexterns_header is None:
            assert self.llexterns_functions is None
            self.llexterns_header, self.llexterns_functions = \
                                   generate_llfile(self.db, extern_decls)

    def create_codewrite(self, func_name):
        # prevent running the same function twice in a test
        if func_name in self.function_count:
            postfix = '_%d' % self.function_count[func_name]
            self.function_count[func_name] += 1
        else:
            postfix = ''
            self.function_count[func_name] = 1
        filename = udir.join(func_name + postfix).new(ext='.ll')
        f = open(str(filename), 'w')
        return CodeWriter(f, self), filename

    def write_extern_decls(self, codewriter, extern_decls):        
        for c_name, obj in extern_decls:
            if isinstance(obj, lltype.LowLevelType):
                if isinstance(obj, lltype.Ptr):
                    obj = obj.TO

                l = "%%%s = type %s" % (c_name, self.db.repr_type(obj))
                codewriter.append(l)

    def write_entry_point(self, codewriter):
        # XXX we need to create our own main() that calls the actual
        # entry_point function
        entryfunc_name = self.entrynode.getdecl().split('%pypy_', 1)[1]
        entryfunc_name = entryfunc_name.split('(')[0]
        print entryfunc_name
        if entryfunc_name not in ["main_noargs", "main"]:
            return
        llcode = extfunctions["%" + entryfunc_name][1]        
        codewriter.append(llcode)

    def _checkpoint(self, msg=None):
        if not self.logging:
            return
        if msg:
            t = (time.time() - self.starttime)
            log('\t%s took %02dm%02ds' % (msg, t/60, t%60))
        else:
            log('GenLLVM:')
        self.starttime = time.time()

    def _print_node_stats(self):
        # disable node stats output
        if not self.logging: 
            return 

        nodecount = {}
        for node in self.db.getnodes():
            typ = type(node)
            try:
                nodecount[typ] += 1
            except:
                nodecount[typ] = 1
        stats = [(count, str(typ)) for typ, count in nodecount.iteritems()]
        stats.sort()
        for s in stats:
            log('STATS %s' % str(s))

def genllvm(translator, gcpolicy=None, exceptionpolicy=None,
            log_source=False, optimize=True, exe_name=None, logging=False):

    gen = GenLLVM(translator,
                  GcPolicy.new(gcpolicy),
                  ExceptionPolicy.new(exceptionpolicy),
                  logging=logging)
    filename = gen.gen_llvm_source()

    if log_source:
        log(open(filename).read())

    if exe_name is not None:
        # standalone
        return build_llvm_module.make_module_from_llvm(gen, filename,
                                                       optimize=optimize,
                                                       exe_name=exe_name)
    else:
        # use pyrex to create module for CPython
        postfix = ''
        basename = filename.purebasename + '_wrapper' + postfix + '.pyx'
        pyxfile = filename.new(basename = basename)
        write_pyx_wrapper(gen, pyxfile)    
        return build_llvm_module.make_module_from_llvm(gen, filename,
                                                       pyxfile=pyxfile,
                                                       optimize=optimize)

def compile_module(function, annotation, view=False, **kwds):
    t = Translator(function)
    a = t.annotate(annotation)
    a.simplify()
    t.specialize()
    t.backend_optimizations(ssa_form=False)
    
    # note: this is without policy transforms
    if view:
        t.view()
    return genllvm(t, **kwds)

def compile_function(function, annotation, **kwds):
    """ Helper - which get the compiled module from CPython. """
    mod = compile_module(function, annotation, **kwds)
    return getattr(mod, 'pypy_' + function.func_name + "_wrapper")
