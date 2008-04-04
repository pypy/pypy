from pypy.translator.cli.cts import CTS
from pypy.translator.cli.database import LowLevelDatabase
from pypy.translator.cli.node import Node
from pypy.rpython.ootypesystem import ootype

def get_entrypoint(graph):
    from pypy.translator.cli.test.runtest import TestEntryPoint
    try:
        ARG0 = graph.getargs()[0].concretetype
    except IndexError:
        ARG0 = None
    if isinstance(ARG0, ootype.List) and ARG0.ITEM is ootype.String:
        return StandaloneEntryPoint(graph)
    else:
        return TestEntryPoint(graph)

class BaseEntryPoint(Node):
    isnetmodule = False
    
    def set_db(self, db):
        self.db = db
        self.cts = CTS(db)

    def ilasm_flags(self):
        return []

    def output_filename(self, il_filename):
        return il_filename.replace('.il', '.exe')


class StandaloneEntryPoint(BaseEntryPoint):
    """
    This class produces a 'main' method that converts the argv in a
    List of Strings and pass it to the real entry point.
    """
    
    def __init__(self, graph_to_call):
        self.graph = graph_to_call

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        try:
            ARG0 = self.graph.getargs()[0].concretetype
        except IndexError:
            ARG0 = None
        assert isinstance(ARG0, ootype.List) and ARG0.ITEM is ootype.String,\
               'Wrong entry point signature: List(String) expected'

        ilasm.begin_function('main', [('string[]', 'argv')], 'void', True, 'static')
        ilasm.new('instance void class [pypylib]pypy.runtime.List`1<string>::.ctor()')

        # fake argv[0]
        ilasm.opcode('dup')
        ilasm.call('class [mscorlib]System.Reflection.Assembly class [mscorlib]System.Reflection.Assembly::GetEntryAssembly()')
        ilasm.call_method('string class [mscorlib]System.Reflection.Assembly::get_Location()', True)
        ilasm.call_method('void class [mscorlib]System.Collections.Generic.List`1<string>::Add(!0)', True)

        # add real argv
        ilasm.opcode('dup')
        ilasm.opcode('ldarg.0')
        ilasm.call_method('void class [mscorlib]System.Collections.Generic.List`1<string>::'
                          'AddRange(class [mscorlib]System.Collections.Generic.IEnumerable`1<!0>)', True)

        ilasm.call(self.cts.graph_to_signature(self.graph))
        ilasm.opcode('pop') # XXX: return this value, if it's an int32
        ilasm.opcode('ret')
        ilasm.end_function()
        self.db.pending_function(self.graph)

class DllEntryPoint(BaseEntryPoint):
    def __init__(self, name, graphs, isnetmodule=False):
        self.name = name
        self.graphs = graphs
        self.isnetmodule = isnetmodule

    def get_name(self):
        return self.name

    def ilasm_flags(self):
        return BaseEntryPoint.ilasm_flags(self) + ['/dll']

    def output_filename(self, il_filename):
        ext = '.dll'
        if self.isnetmodule:
            ext = '.netmodule'
        return il_filename.replace('.il', ext)

    def render(self, ilasm):
        for graph in self.graphs:
            self.db.pending_function(graph)
