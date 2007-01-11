""" basic oogenerator
"""
from pypy.translator.oosupport import constant as ooconst

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
    StaticMethodConst = ooconst.StaticMethodConst
    CustomDictConst = ooconst.CustomDictConst
    DictConst = ooconst.DictConst
    WeakRefConst = ooconst.WeakRefConst

    def __init__(self, tmpdir, translator, entrypoint, config=None):
        self.tmpdir = tmpdir
        self.translator = translator
        self.entrypoint = entrypoint
        self.db = self.Database(self)
        if config is None:
            from pypy.config.pypyoption import get_pypy_config
            config = get_pypy_config(translating=True)
        self.config = config

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
