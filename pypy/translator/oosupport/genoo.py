
""" basic oogenerator
"""

class Tee(object):
    def __init__(self, *args):
        self.outfiles = args

    def write(self, s):
        for outfile in self.outfiles:
            outfile.write(s)

    def close(self):
        for outfile in self.outfiles:
            if outfile is not sys.stdout:
                outfile.close()

class GenOO(object):
    def __init__(self, tmpdir, translator, entrypoint=None, backend_mapping=None, pending_graphs = [],\
        stdout = False):
        
        self.stdout = stdout
        self.backend_mapping = backend_mapping
    #def __init__(self, tmpdir, translator, entrypoint=None, type_system_class=CTS,
    #             opcode_dict=opcodes, name_suffix='.il', function_class=Function,
    #             database_class = LowLevelDatabase, pending_graphs=()):
        self.tmpdir = tmpdir
        self.translator = translator
        self.entrypoint = entrypoint
        self.db = self.backend_mapping['database_class'](self.backend_mapping)

        for graph in pending_graphs:
            self.db.pending_function(graph)

        if entrypoint is None:
            self.assembly_name = self.translator.graphs[0].name
        else:
            self.assembly_name = entrypoint.get_name()

        self.tmpfile = tmpdir.join(self.assembly_name + self.backend_mapping['name_suffix'])

    def generate_source(self):
        out = self.tmpfile.open('w')
        if self.stdout:
            out = Tee(sys.stdout, out)

        self.ilasm = self.backend_mapping['asm_class'](out, self.assembly_name )
        
        # TODO: instance methods that are also called as unbound
        # methods are rendered twice, once within the class and once
        # as an external function. Fix this.
        self.fix_names()
        self.gen_entrypoint()
        while self.db._pending_nodes:
            self.gen_pendings()
            self.db.gen_constants(self.ilasm)
        out.close()
        return self.tmpfile.strpath

    def gen_entrypoint(self):
        if self.entrypoint:
            self.entrypoint.db = self.db
            self.db.pending_node(self.entrypoint)
        else:
            self.db.pending_function(self.translator.graphs[0])

    def gen_pendings(self):
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            node.render(self.ilasm)

    def fix_names(self):
        # it could happen that two distinct graph have the same name;
        # here we assign an unique name to each graph.
        names = set()
        for graph in self.translator.graphs:
            while graph.name in names:
                graph.name += '_'
            names.add(graph.name)
