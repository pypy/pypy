import py
from itertools import count
from pypy.translator.llvm.log import log 

log = log.codewriter 

DEFAULT_TAIL     = ''       #/tail
DEFAULT_CCONV    = 'fastcc'    #ccc/fastcc

class CodeWriter(object): 
    def __init__(self, f, genllvm): 
        self.f = f
        self.genllvm = genllvm
        self.word  = genllvm.db.get_machine_word()
        self.uword = genllvm.db.get_machine_uword()

    def append(self, line): 
        self.f.write(line + '\n')

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
        self.append("%s = %s global %s" % (name, "internal", typeandata))

    def structdef(self, name, typereprs):
        self.append("%s = type { %s }" %(name, ", ".join(typereprs)))

    def arraydef(self, name, lentype, typerepr):
        self.append("%s = type { %s, [0 x %s] }" % (name, lentype, typerepr))

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.append("%s = type %s (%s)" % (name, rettyperepr,
                                           ", ".join(argtypereprs)))

    def declare(self, decl, cconv=DEFAULT_CCONV):
        self.append("declare %s %s" %(cconv, decl,))

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

    def openfunc(self, decl, is_entrynode=False, cconv=DEFAULT_CCONV): 
        self.newline()
        #if is_entrynode:
        #    linkage_type = ''
        #else:
        #    linkage_type = 'internal '
        linkage_type = 'internal '
        self.append("%s%s %s {" % (linkage_type, cconv, decl,))

    def closefunc(self): 
        self.append("}") 

    def ret(self, type_, ref): 
        if type_ == 'void':
            self.indent("ret void")
        else:
            self.indent("ret %s %s" % (type_, ref))

    def phi(self, targetvar, type_, refs, blocknames): 
        assert targetvar.startswith('%')
        assert refs and len(refs) == len(blocknames), "phi node requires blocks" 
        mergelist = ", ".join(
            ["[%s, %%%s]" % item 
                for item in zip(refs, blocknames)])
        s = "%s = phi %s %s" % (targetvar, type_, mergelist)
        self.indent(s)

    def binaryop(self, name, targetvar, type_, ref1, ref2):
        self.indent("%s = %s %s %s, %s" % (targetvar, name, type_, ref1, ref2))

    def shiftop(self, name, targetvar, type_, ref1, ref2):
        self.indent("%s = %s %s %s, ubyte %s" % (targetvar, name, type_, ref1, ref2))

    #from: http://llvm.cs.uiuc.edu/docs/LangRef.html
    #The optional "tail" marker indicates whether the callee function accesses any
    # allocas or varargs in the caller. If the "tail" marker is present, the function
    # call is eligible for tail call optimization. Note that calls may be marked
    # "tail" even if they do not occur before a ret instruction. 
    def call(self, targetvar, returntype, functionref, argrefs, argtypes, label=None, except_label=None, tail=DEFAULT_TAIL, cconv=DEFAULT_CCONV):
        if cconv is not 'fastcc':
            tail_ = ''
        else:
            tail_ = tail
        if tail_:
                tail_ += ' '
        args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])
        if except_label:
            self.genllvm.exceptionpolicy.invoke(self, targetvar, tail_, cconv, returntype, functionref, args, label, except_label)
        else:
            if returntype == 'void':
                self.indent("%scall %s void %s(%s)" % (tail_, cconv, functionref, args))
            else:
                self.indent("%s = %scall %s %s %s(%s)" % (targetvar, tail_, cconv, returntype, functionref, args))

    def cast(self, targetvar, fromtype, fromvar, targettype):
        if fromtype == 'void' and targettype == 'void':
                return
        self.indent("%(targetvar)s = cast %(fromtype)s "
                        "%(fromvar)s to %(targettype)s" % locals())

    def malloc(self, targetvar, type_, size=1, atomic=False, cconv=DEFAULT_CCONV):
        for s in self.genllvm.gcpolicy.malloc(targetvar, type_, size, atomic, self.word, self.uword).split('\n'):
            self.indent(s)

    def getelementptr(self, targetvar, type, typevar, *indices):
        word = self.word
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, %(word)s 0, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self.indent(res)

    def load(self, targetvar, targettype, ptr):
        self.indent("%(targetvar)s = load %(targettype)s* %(ptr)s" % locals())

    def store(self, valuetype, valuevar, ptr): 
        self.indent("store %(valuetype)s %(valuevar)s, "
                    "%(valuetype)s* %(ptr)s" % locals())

    def debugcomment(self, tempname, len, tmpname):
        word = self.word
        res = "%s = call ccc %(word)s (sbyte*, ...)* %%printf(" % locals()
        res += "sbyte* getelementptr ([%s x sbyte]* %s, %(word)s 0, %(word)s 0) )" % locals()
        res = res % (tmpname, len, tmpname)
        self.indent(res)
