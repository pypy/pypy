import types
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.node import Node

IEQUALITY_COMPARER = 'class [mscorlib]System.Collections.Generic.IEqualityComparer`1<%s>'

class EqualityComparer(Node):
    count = 0
    
    def __init__(self, db, KEY_TYPE, eq_args, hash_args):
        self.db = db
        self.cts = CTS(db)
        self.KEY_TYPE = KEY_TYPE
        self.key_type = self.cts.lltype_to_cts(KEY_TYPE)
        self.eq_args = eq_args
        self.hash_args = hash_args
        self.name = 'EqualityComparer_%d' % EqualityComparer.count
        EqualityComparer.count += 1

    def get_ctor(self):
        return 'instance void %s::.ctor()' % self.name

    def render(self, ilasm):
        self.ilasm = ilasm
        IEqualityComparer = IEQUALITY_COMPARER % self.key_type
        ilasm.begin_class(self.name, interfaces=[IEqualityComparer])
        self._ctor()
        self._method('Equals', [(self.key_type, 'x'), (self.key_type, 'y')],
                     'bool', self.eq_args)
        self._method('GetHashCode', [(self.key_type, 'x')], 'int32', self.hash_args)
        ilasm.end_class()

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void [mscorlib]System.Object::.ctor()')
        self.ilasm.opcode('ret')
        self.ilasm.end_function()
        
    def _method(self, name, arglist, return_type, fn_args):
        self.ilasm.begin_function(name, arglist, return_type, False,
                                  'final', 'virtual', 'hidebysig', 'newslot',
                                  'instance', 'default')

        if type(fn_args) == types.FunctionType:
            assert len(fn_args.self_arg) <= 1
            if len(fn_args.self_arg) == 1:
                assert fn_args.graph.getargs()[0].concretetype is ootype.Void
            self._call_function(fn_args.graph, len(arglist))
        else:
            fn, obj, method_name = fn_args
            # fn is a Constant(StaticMethod)
            if method_name.value is None:
                self._call_function(fn.value.graph, len(arglist))
            else:
                assert False, 'XXX'

        self.ilasm.end_function()

    def _call_function(self, graph, n_args):
        self.db.pending_function(graph)
        for arg in range(1, n_args+1):
            self.ilasm.opcode('ldarg', arg)
        signature = self.cts.graph_to_signature(graph)
        self.ilasm.call(signature)
        self.ilasm.opcode('ret')
