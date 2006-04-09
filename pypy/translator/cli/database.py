from pypy.translator.cli.cts import CTS
from pypy.translator.cli.function import Function
from pypy.translator.cli.class_ import Class
from pypy.rpython.ootypesystem import ootype

try:
    set
except NameError:
    from sets import Set as set

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASS = 'Constants'

class LowLevelDatabase(object):
    def __init__(self):
        self._pending_nodes = set()
        self._rendered_nodes = set()
        self.classes = {} # classdef --> class_name
        self.functions = {} # graph --> function_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> const_name

    def pending_function(self, graph):
        self.pending_node(Function(self, graph))

    def pending_class(self, classdef):
        self.pending_node(Class(self, classdef))

    def pending_node(self, node):
        if node in self._pending_nodes or node in self._rendered_nodes:
            return
        self._pending_nodes.add(node)

    def record_function(self, graph, name):
        self.functions[graph] = name

    def record_class(self, classdef, name):
        self.classes[classdef] = name

    def function_name(self, graph):
        return self.functions.get(graph, None)

    def class_name(self, classdef):
        return self.classes.get(classdef, None)

    def record_const(self, value):
        const = AbstractConst.make(self, value)
        name = const.get_name(len(self.consts))
        self.consts[const] = name
        return '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, name)

    def gen_constants(self, ilasm):
        ilasm.begin_namespace(CONST_NAMESPACE)
        ilasm.begin_class(CONST_CLASS)

        # render field definitions
        for const, name in self.consts.iteritems():
            ilasm.field(name, const.get_type(), static=True)

        # initialize fields
        ilasm.begin_function('.cctor', [], 'void', False, 'static',
                             'specialname', 'rtspecialname', 'default')
        for const, name in self.consts.iteritems():
            const.init(ilasm)
            type_ = const.get_type()
            ilasm.opcode('stsfld %s %s.%s::%s' % (type_, CONST_NAMESPACE, CONST_CLASS, name))

        ilasm.opcode('ret')
        ilasm.end_function()

        ilasm.end_class()
        ilasm.end_namespace()


class AbstractConst(object):
    def make(db, const):
        if isinstance(const, ootype._view):
            const = const._inst
        if isinstance(const, ootype._instance):
            return InstanceConst(db, const)
        else:
            assert False, 'Unknown constant: %s' % const
    make = staticmethod(make)
    
    def get_name(self, n):
        pass

    def get_type(self):
        pass

    def init(self, ilasm):
        pass

class InstanceConst(AbstractConst):
    def __init__(self, db, obj):
        self.cts = CTS(db)
        self.obj = obj

    def get_name(self, n):
        name = self.obj._TYPE._name.replace('.', '_')
        return '%s_%d' % (name, n)

    def get_type(self):
        return self.cts.lltype_to_cts(self.obj._TYPE)
        #return 'class %s' % self.obj._TYPE._name

    def init(self, ilasm):
        classdef = self.obj._TYPE        
        ilasm.new('instance void class %s::.ctor()' % classdef._name)
        while classdef is not None:
            for name, (type_, value) in classdef._fields.iteritems():
                if isinstance(type_, ootype.StaticMethod):
                    continue
                elif type_ is ootype.Class:
                    continue
            classdef = classdef._superclass
