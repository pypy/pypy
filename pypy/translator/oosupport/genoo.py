""" basic oogenerator
"""

from py.builtin import set
from pypy.translator.oosupport import constant as ooconst
from pypy.translator.oosupport.treebuilder import build_trees
from pypy.translator.backendopt.ssa import SSI_to_SSA

class GenOO(object):
    TypeSystem = None
    Function = None
    Database = None
    opcodes = None
    log = None

    # Defines the subclasses used to represent complex constants by
    # _create_complex_const:
    
    ConstantGenerator = None
    NullConst = ooconst.NullConst
    InstanceConst = ooconst.InstanceConst
    RecordConst = ooconst.RecordConst
    ClassConst = ooconst.ClassConst
    ListConst = ooconst.ListConst
    ArrayConst = ooconst.ArrayConst
    StaticMethodConst = ooconst.StaticMethodConst
    CustomDictConst = ooconst.CustomDictConst
    DictConst = ooconst.DictConst
    WeakRefConst = ooconst.WeakRefConst

    def __init__(self, tmpdir, translator, entrypoint, config=None, exctrans=False):
        self.tmpdir = tmpdir
        self.translator = translator
        self.entrypoint = entrypoint
        self.db = self.Database(self)
        if config is None:
            from pypy.config.pypyoption import get_pypy_config
            config = get_pypy_config(translating=True)
        self.config = config

        # XXX: move this option out of the 'cli' section
        exctrans = exctrans or translator.config.translation.cli.exception_transformer
        if exctrans:
            self.db.exceptiontransformer = translator.getexceptiontransformer()

        self.append_prebuilt_nodes()

        if exctrans:
            etrafo = self.db.exceptiontransformer
            for graph in translator.graphs:
                etrafo.create_exception_handling(graph)

        if translator.config.translation.backendopt.stack_optimization:
            self.stack_optimization()

    def stack_optimization(self):
        for graph in self.translator.graphs:
            SSI_to_SSA(graph)
            build_trees(graph)

    def append_prebuilt_nodes(self):
        pass

    def generate_source(self):
        self.ilasm = self.create_assembler()
        self.fix_names()
        self.gen_entrypoint()
        self.gen_pendings()
        self.db.gen_constants(self.ilasm)
        self.ilasm.close()

    def gen_entrypoint(self):
        if self.entrypoint:
            self.entrypoint.set_db(self.db)
            self.db.pending_node(self.entrypoint)
        else:
            self.db.pending_function(self.translator.graphs[0])

    def gen_pendings(self):
        n = 0
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            node.render(self.ilasm)
            self.db._rendered_nodes.add(node)
            n+=1
            if (n%100) == 0:
                total = len(self.db._pending_nodes) + n
                self.log.graphs('Rendered %d/%d (approx. %.2f%%)' %\
                           (n, total, n*100.0/total))

    def fix_names(self):
        # it could happen that two distinct graph have the same name;
        # here we assign an unique name to each graph.
        names = set()
        for graph in self.translator.graphs:
            base_name = graph.name
            i = 0
            while graph.name in names:
                graph.name = '%s_%d' % (base_name, i)
                i+=1
            names.add(graph.name)

    def create_assembler(self):
        raise NotImplementedError
