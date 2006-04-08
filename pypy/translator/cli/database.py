from pypy.rpython.ootypesystem import ootype

try:
    set
except NameError:
    from sets import Set as set

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASS = 'Constants'

class LowLevelDatabase(object):
    def __init__(self):
        self.classes = set()
        self.pending_graphs = []
        self.functions = {} # graph --> function_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> const_name

    def record_function(self, graph, name):
        self.functions[graph] = name

    def function_name(self, graph):
        return self.functions.get(graph, None)

    def record_const(self, value):
        const = AbstractConst.make(value)
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
    def make(const):
        if isinstance(const, ootype._view):
            const = const._inst
        if isinstance(const, ootype._instance):
            return InstanceConst(const)
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
    def __init__(self, obj):
        self.obj = obj

    def get_name(self, n):
        name = self.obj._TYPE._name.replace('.', '_')
        return '%s_%d' % (name, n)

    def get_type(self):
        return 'class %s' % self.obj._TYPE._name

    def init(self, ilasm):
        classdef = self.obj._TYPE        
        ilasm.new('instance void class %s::.ctor()' % classdef._name)
        # TODO: initialize fields
