import py
from itertools import count
from pypy.translator.llvm2.log import log 

log = log.codewriter 
show_line_numbers = True # False
count = count().next

class CodeWriter(object): 
    def __init__(self): 
        self._lines = []

    def append(self, line): 
        if show_line_numbers:
            line = "%-75s; %d" % (line, len(self._lines) + 1)
        self._lines.append(line) 
        log(line) 

    def comment(self, line, indent=False):
        line = ";; " + line
        if indent:
            self.indent(line)
        else:
            self.append(line)

    def newline(self):
        self.append("")

    def indent(self, line): 
        self.append("        " + line) 

    def label(self, name):
        self.append("    %s:" % name)

    def globalinstance(self, name, typeandata):
        self.append("%s = constant %s" % (name, typeandata))

    def structdef(self, name, typereprs):
        self.append("%s = type { %s }" %(name, ", ".join(typereprs)))

    def arraydef(self, name, typerepr):
        self.append("%s = type { int, [0 x %s] }" % (name, typerepr))

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.append("%s = type %s (%s)" % (name, rettyperepr,
                                           ", ".join(argtypereprs)))

    def declare(self, decl):
        self.append("declare %s" %(decl,))

    def startimpl(self):
        self.append("")
        self.append("implementation")
        self.append("")

    def br_uncond(self, blockname): 
        self.indent("br label %%%s" %(blockname,))

    def br(self, switch, blockname_false, blockname_true):
        self.indent("br bool %s, label %%%s, label %%%s"
                    % (switch, blockname_true, blockname_false))

    def openfunc(self, decl): 
        self.append("%s {" % (decl,))

    def closefunc(self): 
        self.append("}") 

    def ret(self, type_, ref): 
        self.indent("ret %s %s" % (type_, ref))

    def ret_void(self):
        self.indent("ret void")

    def phi(self, targetvar, type_, refs, blocknames): 
        assert targetvar.startswith('%')
        assert refs and len(refs) == len(blocknames), "phi node requires blocks" 
        mergelist = ", ".join(
            ["[%s, %%%s]" % item 
                for item in zip(refs, blocknames)])
        self.indent("%s = phi %s %s" %(targetvar, type_, mergelist))

    def binaryop(self, name, targetvar, type_, ref1, ref2):
        self.indent("%s = %s %s %s, %s" % (targetvar, name, type_, ref1, ref2))

    def call(self, targetvar, returntype, functionref, argrefs, argtypes):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("%s = call %s %s(%s)" % (targetvar, returntype, functionref,
                                             ", ".join(arglist)))

    def call_void(self, functionref, argrefs, argtypes):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("call void %s(%s)" % (functionref, ", ".join(arglist)))

    def cast(self, targetvar, fromtype, fromvar, targettype):
        self.indent("%(targetvar)s = cast %(fromtype)s "
                        "%(fromvar)s to %(targettype)s" % locals())

    def malloc(self, targetvar, type_, size=1, atomic=False):
        cnt = count()
        postfix = ('', '_atomic')[atomic]
        self.indent("%%malloc.Size.%(cnt)d = getelementptr %(type_)s* null, uint %(size)s" % locals())
        self.indent("%%malloc.SizeU.%(cnt)d = cast %(type_)s* %%malloc.Size.%(cnt)d to uint" % locals())
        self.indent("%%malloc.Ptr.%(cnt)d = call sbyte* %%gc_malloc%(postfix)s(uint %%malloc.SizeU.%(cnt)d)" % locals())
        self.indent("%(targetvar)s = cast sbyte* %%malloc.Ptr.%(cnt)d to %(type_)s*" % locals())

    def getelementptr(self, targetvar, type, typevar, *indices):
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, int 0, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self.indent(res)

    def load(self, targetvar, targettype, ptr):
        self.indent("%(targetvar)s = load %(targettype)s* %(ptr)s" % locals())

    def store(self, valuetype, valuevar, ptr): 
        self.indent("store %(valuetype)s %(valuevar)s, "
                    "%(valuetype)s* %(ptr)s" % locals())

    def __str__(self): 
        return "\n".join(self._lines)
