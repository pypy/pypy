from pypy.translator.gensupp import NameManager
from pypy.translator.squeak.node import FunctionNode, ClassNode, SetupNode
from pypy.translator.squeak.node import MethodNode, SetterNode, GetterNode
from pypy.rpython.ootypesystem.ootype import Record
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

    def gen(self):
        graph = self.translator.graphs[0]
        self.pending_nodes.append(FunctionNode(self, graph))
        self.filename = '%s.st' % graph.name
        file = self.sqdir.join(self.filename).open('w')
        self.gen_source(file)
        self.pending_nodes.append(SetupNode(self, self.constant_insts)) 
        self.gen_source(file)
        file.close()
        return self.filename

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

    def unique_func_name(self, funcgraph, schedule=True):
        function = funcgraph.func
        squeak_func_name = self.unique_name(function, function.__name__)
        if schedule:
            self.schedule_node(FunctionNode(self, funcgraph))
        return squeak_func_name
        
    def unique_method_name(self, INSTANCE, method_name, schedule=True):
        # XXX it's actually more complicated than that because of
        # inheritance ...
        squeak_method_name = self.unique_name(
                (INSTANCE, method_name), method_name)
        if schedule:
            self.schedule_node(MethodNode(self, INSTANCE, method_name))
        return squeak_method_name
        
    def unique_class_name(self, INSTANCE):
        class_node = self.schedule_node(ClassNode(self, INSTANCE))
        if isinstance(INSTANCE, Record): # XXX quick hack
            class_name = "Record"
        else:
            class_name = INSTANCE._name.split(".")[-1]
        squeak_class_name = self.unique_name(INSTANCE, class_name)
        return "Py%s" % squeak_class_name

    def unique_field_name(self, INSTANCE, field_name, schedule=True):
        # XXX nameclashes with superclasses must be considered, too.
        while not INSTANCE._fields.has_key(field_name):
            # This is necessary to prevent a field from having different
            # unique names in different subclasses.
            INSTANCE = INSTANCE._superclass
        if schedule:
            # Generating getters and setters for all fields by default which
            # is potentially a waste, but easier for now.
            self.schedule_node(SetterNode(self, INSTANCE, field_name))
            self.schedule_node(GetterNode(self, INSTANCE, field_name))
        return self.unique_name(
                (INSTANCE, "field", field_name), field_name)

    def unique_var_name(self, variable):
        return self.unique_name(variable, variable.name)

    def unique_name(self, key, basename):
        # XXX should account for squeak keywords here
        if self.unique_name_mapping.has_key(key):
            unique = self.unique_name_mapping[key]
        else:
            camel_basename = camel_case(basename)
            unique = self.name_manager.uniquename(camel_basename)
            self.unique_name_mapping[key] = unique
        return unique


def camel_case(identifier):
    identifier = identifier.replace(".", "_")
    words = identifier.split('_')
    return ''.join([words[0]] + [w.capitalize() for w in words[1:]])

