import string

from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS

class Record(Node):
    def __init__(self, db, record):
        self.db = db
        self.cts = CTS(db)
        self.record = record

        trans = string.maketrans('(),', '___')
        name = ['Record']
        for f_name, (f_type, f_default) in record._fields.iteritems():
            type_name = f_type._short_name().translate(trans)
            name.append(type_name)
        self.name = '__'.join(name)
        record._name = self.name

    def __hash__(self):
        return hash(self.record)

    def __eq__(self, other):
        return self.record == other.record

    def get_name(self):
        return self.name

    def get_base_class(self):
        return '[mscorlib]System.Object'        

    def render(self, ilasm):
        if self.db.class_name(self.record) is not None:
            return # already rendered

        self.ilasm = ilasm

        ilasm.begin_class(self.name, self.get_base_class())
        for f_name, (f_type, f_default) in self.record._fields.iteritems():
            cts_type = self.cts.lltype_to_cts(f_type)
            if cts_type != 'void':
                ilasm.field(f_name, cts_type)

        self._ctor()
        ilasm.end_class()

        self.db.record_class(self.record, self.name)

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void %s::.ctor()' % self.get_base_class())
        self.ilasm.opcode('ret')
        self.ilasm.end_function()
        
