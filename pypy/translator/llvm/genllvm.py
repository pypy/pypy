import time

from pypy.tool.isolate import Isolate 

from pypy.translator.llvm import buildllvm
from pypy.translator.llvm.database import Database 
from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.translator.llvm.codewriter import CodeWriter
from pypy.translator.llvm import extfuncnode
from pypy.translator.llvm.module.support import \
     extdeclarations, extfunctions, extfunctions_standalone, write_raise_exc
from pypy.translator.llvm.node import Node
from pypy.translator.llvm.externs2ll import setup_externs, generate_llfile
from pypy.translator.llvm.gc import GcPolicy
from pypy.translator.llvm.log import log

class GenLLVM(object):
    # see create_codewriter() below
    function_count = {}

    def __init__(self, translator, standalone):
    
        # reset counters
        Node.nodename_count = {}    

        self.standalone = standalone
        self.translator = translator
        
        self.config = translator.config

    def gen_source(self, func):
        self._checkpoint()

        codewriter = self.setup(func)

        # write top part of llvm file
        self.write_headers(codewriter)

        codewriter.startimpl()

        # write bottom part of llvm file
        self.write_implementations(codewriter)

        # write entry point if there is one
        codewriter.comment("End of file")
        codewriter.close()
        self._checkpoint('done')

        return self.filename

    def setup(self, func):
        """ setup all nodes
            create c file for externs
            create ll file for c file
            create codewriter """

        # XXX please dont ask!
        from pypy.translator.c.genc import CStandaloneBuilder
        cbuild = CStandaloneBuilder(self.translator, func, config=self.config)
        #cbuild.stackless = self.stackless
        c_db = cbuild.generate_graphs_for_llinterp()

        self.db = Database(self, self.translator)

        # XXX hardcoded for now
        self.db.gcpolicy = GcPolicy.new(self.db, 'boehm')

        # get entry point
        entry_point = self.get_entry_point(func)
        self._checkpoint('get_entry_point')
        
        # set up all nodes
        self.db.setup_all()
        
        self.entrynode = self.db.set_entrynode(entry_point)
        self._checkpoint('setup_all all nodes')

        # set up externs nodes
        self.extern_decls = setup_externs(c_db, self.db)
        self.translator.rtyper.specialize_more_blocks()
        self.db.setup_all()
        self._checkpoint('setup_all externs')

        for node in self.db.getnodes():
            node.post_setup_transform()
        
        self._print_node_stats()

        # open file & create codewriter
        codewriter, self.filename = self.create_codewriter()
        self._checkpoint('open file and create codewriter')        

        # create ll file from c code
        self.generate_ll_externs(codewriter)
        self._checkpoint('setup_externs')

        return codewriter

    def write_headers(self, codewriter):
        # write external function headers
        codewriter.header_comment('External Function Headers')
        codewriter.write_lines(self.llexterns_header)

        codewriter.header_comment("Type Declarations")

        # write extern type declarations
        self.write_extern_decls(codewriter)
        self._checkpoint('write externs type declarations')

        # write node type declarations
        for typ_decl in self.db.gettypedefnodes():
            typ_decl.writetypedef(codewriter)
        self._checkpoint('write data type declarations')

        codewriter.header_comment("Global Data")

        # write pbcs
        for node in self.db.getnodes():
            # XXX tmp
            if hasattr(node, "writeglobalconstants"):
                node.writeglobalconstants(codewriter)
        self._checkpoint('write global constants')

        codewriter.header_comment("Function Prototypes")

        # write external protos
        codewriter.write_lines(extdeclarations, patch=True)

        # write node protos
        for node in self.db.getnodes():
            if hasattr(node, 'writedecl'):
                node.writedecl(codewriter)

        self._checkpoint('write function prototypes')

    def write_implementations(self, codewriter):
        codewriter.header_comment("Function Implementation")

        # write external function implementations
        codewriter.header_comment('External Function Implementation')
        codewriter.write_lines(self.llexterns_functions)
        codewriter.write_lines(extfunctions, patch=True)
        if self.standalone:
            codewriter.write_lines(extfunctions_standalone, patch=True)
        self.write_extern_impls(codewriter)
        self.write_setup_impl(codewriter)
        
        self._checkpoint('write support implentations')

        # write all node implementations
        for node in self.db.getnodes():
            if hasattr(node, 'writeimpl'):
                node.writeimpl(codewriter)

        self._checkpoint('write node implementations')
    
    def get_entry_point(self, func):
        assert func is not None
        self.entrypoint = func

        bk = self.translator.annotator.bookkeeper
        ptr = getfunctionptr(bk.getdesc(func).getuniquegraph())
        c = inputconst(lltype.typeOf(ptr), ptr)
        self.db.prepare_arg_value(c)
        
        # ensure unqiue entry node name for testing
        entry_node = self.db.obj2node[c.value._obj]
        name = entry_node.name
        if name in self.function_count:
            self.function_count[name] += 1
            name += '_%d' % self.function_count[name]
            entry_node.name =  name
        else:
            self.function_count[name] = 1

        self.entry_name = name[6:]
        return c.value._obj 

    def generate_ll_externs(self, codewriter):
        c_includes = {}
        c_sources = {}

        for node in self.db.getnodes():
            includes, sources = node.external_c_source()            
            for include in includes:
                c_includes[include] = True
            for source in sources:
                c_sources[source] = True

        self.llexterns_header, self.llexterns_functions = \
                               generate_llfile(self.db,
                                               self.extern_decls,
                                               self.entrynode,
                                               c_includes,
                                               c_sources,
                                               self.standalone, 
                                               codewriter.cconv)

    def create_codewriter(self):
        # prevent running the same function twice in a test
        filename = udir.join(self.entry_name).new(ext='.ll')
        f = open(str(filename), 'w')
        if self.standalone:
            return CodeWriter(f, self.db), filename
        else:
            return CodeWriter(f, self.db, cconv='ccc', linkage=''), filename

    def write_extern_decls(self, codewriter):        
        for c_name, obj in self.extern_decls:
            if isinstance(obj, lltype.LowLevelType):
                if isinstance(obj, lltype.Ptr):
                    obj = obj.TO

                l = "%%%s = type %s" % (c_name, self.db.repr_type(obj))
                codewriter.write_lines(l)
                
    def write_extern_impls(self, codewriter):
        for c_name, obj in self.extern_decls:
            if c_name.startswith("RPyExc_"):
                c_name = c_name[1:]
                exc_repr = self.db.repr_constant(obj)[1]
                write_raise_exc(c_name, exc_repr, codewriter)

    def write_setup_impl(self, codewriter):
        open_decl =  "sbyte* %LLVM_RPython_StartupCode()"
        codewriter.openfunc(open_decl)
        for node in self.db.getnodes():
            node.writesetupcode(codewriter)

        codewriter.ret("sbyte*", "null")
        codewriter.closefunc()

    def compile_module(self):
        assert not self.standalone
        
        modname, dirpath = buildllvm.Builder(self).make_module()
        mod, wrap_fun = self.get_module(modname, dirpath)
        return mod, wrap_fun

    def get_module(self, modname, dirpath):
        if self.config.translation.llvm.isolate:
            mod = Isolate((dirpath, modname))
        else:
            from pypy.translator.tool.cbuild import import_module_from_directory
            mod = import_module_from_directory(dirpath, modname)

        wrap_fun = getattr(mod, 'entrypoint')
        return mod, wrap_fun

    def compile_standalone(self, exe_name):
        assert self.standalone
        return buildllvm.Builder(self).make_standalone(exe_name)

    def _checkpoint(self, msg=None):
        if not self.config.translation.llvm.logging:
            return
        if msg:
            t = (time.time() - self.starttime)
            log('\t%s took %02dm%02ds' % (msg, t/60, t%60))
        else:
            log('GenLLVM:')
        self.starttime = time.time()

    def _print_node_stats(self):
        # disable node stats output
        if not self.config.translation.llvm.logging: 
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

