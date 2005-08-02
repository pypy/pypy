import py
from itertools import count
from pypy.translator.llvm2.log import log 

log = log.codewriter 
show_line_numbers = False # True
count = count().next

class CodeWriter(object): 
    def __init__(self): 
        self._lines = []

    def append(self, line): 
        if show_line_numbers:
            line = "%-75s; %d" % (line, len(self._lines) + 1)
        self._lines.append(line) 

    def comment(self, line, indent=True):
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
        self.newline()
        self.append("    %s:" % name)

    def globalinstance(self, name, typeandata):
        self.append("%s = global %s" % (name, typeandata))

    def structdef(self, name, typereprs):
        self.append("%s = type { %s }" %(name, ", ".join(typereprs)))

    def arraydef(self, name, typerepr):
        self.append("%s = type { int, [0 x %s] }" % (name, typerepr))

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.append("%s = type %s (%s)" % (name, rettyperepr,
                                           ", ".join(argtypereprs)))

    def declare(self, decl):
        self.append("declare fastcc %s" %(decl,))

    def startimpl(self):
        self.newline()
        self.append("implementation")
        self.newline()

    def br_uncond(self, blockname): 
        self.indent("br label %%%s" %(blockname,))

    def br(self, cond, blockname_false, blockname_true):
        self.indent("br bool %s, label %%%s, label %%%s"
                    % (cond, blockname_true, blockname_false))

    def switch(self, intty, cond, defaultdest, value_label):
        labels = ''
        for value, label in value_label:
            labels += ' %s %s, label %%%s' % (intty, value, label)
        self.indent("switch %s %s, label %%%s [%s ]"
                    % (intty, cond, defaultdest, labels))

    def openfunc(self, decl): 
        self.newline()
        self.append("fastcc %s {" % (decl,))

    def closefunc(self): 
        self.append("}") 

    def ret(self, type_, ref): 
        self.indent("ret %s %s" % (type_, ref))

    def ret_void(self):
        self.indent("ret void")

    def unwind(self):
        self.indent("unwind")

    def phi(self, targetvar, type_, refs, blocknames): 
        assert targetvar.startswith('%')
        assert refs and len(refs) == len(blocknames), "phi node requires blocks" 
        mergelist = ", ".join(
            ["[%s, %%%s]" % item 
                for item in zip(refs, blocknames)])
        self.indent("%s = phi %s %s" %(targetvar, type_, mergelist))

    def binaryop(self, name, targetvar, type_, ref1, ref2):
        self.indent("%s = %s %s %s, %s" % (targetvar, name, type_, ref1, ref2))

    def shiftop(self, name, targetvar, type_, ref1, ref2):
        self.indent("%s = %s %s %s, ubyte %s" % (targetvar, name, type_, ref1, ref2))

    def call(self, targetvar, returntype, functionref, argrefs, argtypes):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("%s = call fastcc %s %s(%s)" % (targetvar, returntype, functionref,
                                             ", ".join(arglist)))

    def call_void(self, functionref, argrefs, argtypes):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("call fastcc void %s(%s)" % (functionref, ", ".join(arglist)))

    def invoke(self, targetvar, returntype, functionref, argrefs, argtypes, label, except_label):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("%s = invoke fastcc %s %s(%s) to label %%%s except label %%%s" % (targetvar, returntype, functionref,
                                             ", ".join(arglist), label, except_label))

    def invoke_void(self, functionref, argrefs, argtypes, label, except_label):
        arglist = ["%s %s" % item for item in zip(argtypes, argrefs)]
        self.indent("invoke fastcc void %s(%s) to label %%%s except label %%%s" % (functionref, ", ".join(arglist), label, except_label))

    def cast(self, targetvar, fromtype, fromvar, targettype):
        self.indent("%(targetvar)s = cast %(fromtype)s "
                        "%(fromvar)s to %(targettype)s" % locals())

    def malloc(self, targetvar, type_, size=1, atomic=False):
        cnt = count()
        postfix = ('', '_atomic')[atomic]
        self.indent("%%malloc.Size.%(cnt)d = getelementptr %(type_)s* null, uint %(size)s" % locals())
        self.indent("%%malloc.SizeU.%(cnt)d = cast %(type_)s* %%malloc.Size.%(cnt)d to uint" % locals())
        self.indent("%%malloc.Ptr.%(cnt)d = call fastcc sbyte* %%gc_malloc%(postfix)s(uint %%malloc.SizeU.%(cnt)d)" % locals())
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

    def debugcomment(self, tempname, len, tmpname):
        res = "%s = tail call ccc int (sbyte*, ...)* %%printf("
        res += "sbyte* getelementptr ([%s x sbyte]* %s, int 0, int 0) )"
        res = res % (tmpname, len, tmpname)
        self.indent(res)
        
    def __str__(self): 
        return "\n".join(self._lines)
