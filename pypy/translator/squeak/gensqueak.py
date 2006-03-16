from pypy.translator.gensupp import NameManager
from pypy.translator.squeak.codeformatter import camel_case
from pypy.translator.squeak.node import FunctionNode, ClassNode, SetupNode
try:
    set
except NameError:
    from sets import Set as set


class GenSqueak:

    def __init__(self, sqdir, translator, modname=None):
        self.sqdir = sqdir
        self.translator = translator
        self.modname = (modname or
                        translator.graphs[0].name)

        self.name_manager = NameManager(number_sep="")
        self.unique_name_mapping = {}
        self.pending_nodes = []
        self.generated_nodes = set()
        self.constant_insts = {}

        graph = self.translator.graphs[0]
        self.pending_nodes.append(FunctionNode(self, graph))
        self.filename = '%s.st' % graph.name
        file = self.sqdir.join(self.filename).open('w')
        self.gen_source(file)
        self.pending_nodes.append(SetupNode(self, self.constant_insts)) 
        self.gen_source(file)
        file.close()

    def gen_source(self, file):
        while self.pending_nodes:
            node = self.pending_nodes.pop()
            self.gen_node(node, file)

    def gen_node(self, node, f):
        for dep in node.dependencies():
            if dep not in self.generated_nodes:
                self.pending_nodes.append(node)
                self.schedule_node(dep)
                return
        self.generated_nodes.add(node)
        for line in node.render():
            print >> f, line
        print >> f, ""

    def schedule_node(self, node):
        if node not in self.generated_nodes:
            if node in self.pending_nodes:
                # We move the node to the front so we can enforce
                # the generation of dependencies.
                self.pending_nodes.remove(node)
            self.pending_nodes.append(node)

    def unique_func_name(self, function):
        # XXX do FunctionNode registering here
        squeak_func_name = self.unique_name(function, function.__name__)
        return squeak_func_name
        
    def unique_name(self, key, basename):
        if self.unique_name_mapping.has_key(key):
            unique = self.unique_name_mapping[key]
        else:
            camel_basename = camel_case(basename)
            unique = self.name_manager.uniquename(camel_basename)
            self.unique_name_mapping[key] = unique
        return unique


