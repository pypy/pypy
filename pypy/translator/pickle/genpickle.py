"""
Generate a Python source file from the flowmodel.
The purpose is to create something that allows
to restart code generation after flowing and maybe
annotation.
"""
import autopath, os
from pypy.objspace.flow.model import Constant, Variable, Block, Link
from pypy.objspace.flow.flowcontext import SpamBlock, EggBlock
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph

from pypy.tool.tls import tlsobject
from pypy.translator.gensupp import uniquemodulename, NameManager

from pypy.translator.c.pyobj import PyObjMaker

# XXX the latter import is temporary.
# I think we will refactor again and
# put a slightly more general module
# into ./..

# ____________________________________________________________


class GenPickle(PyObjMaker):

    def __init__(self, translator):
        self.translator = translator
        PyObjMaker.__init__(self, NameManager(), None)
        self.initcode.append("""\
from pypy.objspace.flow.model import Constant, Variable, Block, Link
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph
from pypy.translator.translator import Translator""")

    def nameof(self, obj):
        try:
            return self.dispatch[type(obj)](self, obj)
        except KeyError:
            return self.computenameof(obj)

    def computenameof(self, obj):
        # XXX PyObjMaker should probably be less greedy
        if type(obj) in self.dispatch:
            return self.dispatch[type(obj)](self, obj)
        return PyObjMaker.computenameof(self, obj)

    dispatch = {}

    def nameof_Constant(self, obj):
        name = self.uniquename("gcon")
        value = self.nameof(obj.value)
        self.initcode.append("%s = Constant(%s)" % (name, value))
        if hasattr(obj, "concretetype"):
            concrete = self.nameof(obj.concretetype)
            self.initcode.append("%s.concretetype=%s" % (name, concrete))
        return name
    dispatch[Constant] = nameof_Constant

    def nameof_Variable(self, obj):
        name = self.uniquename("gvar")
        self.initcode.append("%s = Variable(%r)" % (name, obj.name))
        if hasattr(obj, "concretetype"):
            concrete = self.nameof(obj.concretetype)
            self.initcode.append("%s.concretetype=%s" % (name, concrete))
        return name
    dispatch[Variable] = nameof_Variable

    def nameof_Link(self, obj):
        name = self.uniquename("glink")
        args = self.nameof(obj.args)
        target = self.nameof(obj.target)
        exitcase = self.nameof(obj.exitcase)
        ia = self.initcode.append
        ia("%s = Link(%s, %s, %s)" % (args, target, exitcase))
        if obj.last_exception:
            ia("%s.last_exception = %s" % self.nameof(obj.last_exception))
            ia("%s.last_exc_value = %s" % self.nameof(obj.last_exc_value))
        return name
    dispatch[Link] = nameof_Link

    def nameof_Block(self, obj):
        name = self.uniquename("gblock")
        inputargs = self.nameof(obj.inputargs)
        operations = self.nameof(obj.operations)
        exitswitch = self.nameof(obj.exitswitch)
        exits = self.nameof(obj.exits)
        ia = self.initcode.append
        ia("%s = Block(%s)" % (name, inputargs,) )
        ia("%s.operations = %s" % (name, operations) )
        ia("%s.exitswitch = %s" % (name, exitswitch) )
        ia("%s.exits = %s" % (name, exits) )
        if obj.isstartblock: ia("%s.exits = True" % (name, ) )
        if obj.exc_handler: ia("%s.exc_handler = True" % (name, ) )
        return name
    dispatch[Block] = dispatch[SpamBlock] = dispatch[EggBlock] = nameof_Block

    def nameof_SpaceOperation(self, obj):
        name = self.uniquename("gsop")
        opname = self.nameof(intern(obj.opname))
        args = self.nameof(obj.args)
        result = self.nameof(obj.result)
        ia = self.initcode.append
        ia("%s = SpaceOperation(%s, %s, %s)" % (name, opname, args, result) )
        if obj.offset != -1: ia("%s.offset= %d" % (name, obj.offset) )
        return name
    dispatch[SpaceOperation] = nameof_SpaceOperation

    def nameof_FunctionGraph(self,obj):
        name = self.uniquename("gfgraph")

    def nameofconst(self, c, debug=None):
        try:
            concretetype = c.concretetype
        except AttributeError:
            concretetype = self.pyobjtype
        return concretetype.nameof(c.value, debug=debug)

    def nameofvalue(self, value, concretetype=None, debug=None):
        return (concretetype or self.pyobjtype).nameof(value, debug=debug)

    def getfuncdef(self, func):
        if func not in self.funcdefs:
            if self.translator.frozen:
                if func not in self.translator.flowgraphs:
                    return None
            else:
                if (func.func_doc and
                    func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                    return None
            funcdef = FunctionDef(func, self)
            self.funcdefs[func] = funcdef
            self.allfuncdefs.append(funcdef)
            self.pendingfunctions.append(funcdef)
        return self.funcdefs[func]
