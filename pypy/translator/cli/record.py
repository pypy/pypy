import string

from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS

class Record(Node):
    def __init__(self, db, record):
        self.db = db
        self.cts = CTS(db)
        self.record = record

        trans = string.maketrans('<>(), :', '_______')
        name = ['Record']
        for f_name, (FIELD_TYPE, f_default) in record._fields.iteritems():
            type_name = FIELD_TYPE._short_name().translate(trans)
            name.append(type_name)
        self.name = '__'.join(name)
        assert ':' not in self.name
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
        for f_name, (FIELD_TYPE, f_default) in self.record._fields.iteritems():
            cts_type = self.cts.lltype_to_cts(FIELD_TYPE)
            if cts_type != 'void':
                ilasm.field(f_name, cts_type)

        self._ctor()
        self._toString()
        ilasm.end_class()

        self.db.record_class(self.record, self.name)

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void %s::.ctor()' % self.get_base_class())
        self.ilasm.opcode('ret')
        self.ilasm.end_function()
        
    def _toString(self):
        # only for testing purposes, and only if the Record represents a tuple
        from pypy.translator.cli.test.runtest import format_object

        for f_name in self.record._fields:
            if not f_name.startswith('item'):
                return # it's not a tuple

        self.ilasm.begin_function('ToString', [], 'string', False, 'virtual', 'instance', 'default')
        self.ilasm.opcode('ldstr', '""')
        for i in xrange(len(self.record._fields)):
            f_name = 'item%d' % i
            FIELD_TYPE, f_default = self.record._fields[f_name]
            self.ilasm.opcode('ldarg.0')
            f_type = self.cts.lltype_to_cts(FIELD_TYPE)
            self.ilasm.get_field((f_type, self.name, f_name))
            format_object(FIELD_TYPE, self.ilasm)
            self.ilasm.call('string string::Concat(string, string)')
            self.ilasm.opcode('ldstr ", "')
            self.ilasm.call('string string::Concat(string, string)')
        self.ilasm.opcode('ret')
        self.ilasm.end_function()
