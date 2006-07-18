from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.node import Node

class Delegate(Node):
    def __init__(self, db, TYPE, name):
        self.cts = CTS(db)        
        self.TYPE = TYPE
        self.name = name

    def __eq__(self, other):
        return self.TYPE == other.TYPE

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.TYPE)

    def get_name(self):
        return self.name

    def dependencies(self):
        # record we know about result and argument types
        self.cts.lltype_to_cts(self.TYPE.RESULT)
        for ARG in self.TYPE.ARGS:
            self.cts.lltype_to_cts(ARG)


    def render(self, ilasm):
        TYPE = self.TYPE
        ilasm.begin_class(self.name, '[mscorlib]System.MulticastDelegate', sealed=True)
        ilasm.begin_function('.ctor',
                             [('object', "'object'"), ('native int', "'method'")],
                             'void',
                             False,
                             'hidebysig', 'specialname', 'rtspecialname', 'instance', 'default',
                             runtime=True)
        ilasm.end_function()

        resulttype = self.cts.lltype_to_cts(TYPE.RESULT)
        arglist = [(self.cts.lltype_to_cts(ARG), '') for ARG in TYPE.ARGS if ARG is not ootype.Void]
        ilasm.begin_function('Invoke', arglist, resulttype, False,
                             'virtual', 'hidebysig', 'instance', 'default',
                             runtime=True)
        ilasm.end_function()
        ilasm.end_class()
