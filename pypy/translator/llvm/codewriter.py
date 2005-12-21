from pypy.translator.llvm.log import log 

log = log.codewriter 

DEFAULT_TAIL     = ''       #/tail
DEFAULT_CCONV    = 'fastcc'    #ccc/fastcc

class CodeWriter(object): 
    def __init__(self, file, db): 
        self.file = file
        self.word_repr = db.get_machine_word()

    def _resolvetail(self, tail, cconv):
        # from: http://llvm.cs.uiuc.edu/docs/LangRef.html
        # The optional "tail" marker indicates whether the callee function
        # accesses any allocas or varargs in the caller. If the "tail" marker
        # is present, the function call is eligible for tail call
        # optimization. Note that calls may be marked "tail" even if they do
        # not occur before a ret instruction.

        if cconv is not 'fastcc':
            tail_ = ''
        else:
            tail_ = tail
        if tail_:
            tail_ += ' '
        return tail_

    # keep these two internal for now - incase we try a different API
    def _append(self, line): 
        self.file.write(line + '\n')

    def _indent(self, line): 
        self._append("        " + line) 

    def write_lines(self, lines):
        for l in lines.split("\n"):
            self._append(l)
    
    def comment(self, line, indent=True):
        line = ";; " + line
        if indent:
            self._indent(line)
        else:
            self._append(line)

    def header_comment(self, s):
        self.newline()
        self.comment(s)
        self.newline()

    def newline(self):
        self._append("")

    def label(self, name):
        self.newline()
        self._append("    %s:" % name)

    def globalinstance(self, name, typeandata):
        self._append("%s = %s global %s" % (name, "internal", typeandata))

    def typedef(self, name, type_):
        self._append("%s = type %s" % (name, type_))

    def structdef(self, name, typereprs):
        self.typedef(name, "{ %s }" % ", ".join(typereprs))

    def arraydef(self, name, lentype, typerepr):
        self.typedef(name, "{ %s, [0 x %s] }" % (lentype, typerepr))

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.typedef(name, "%s (%s)" % (rettyperepr,
                                        ", ".join(argtypereprs)))

    def declare(self, decl, cconv=DEFAULT_CCONV):
        self._append("declare %s %s" %(cconv, decl,))

    def startimpl(self):
        self.newline()
        self._append("implementation")
        self.newline()

    def br_uncond(self, blockname): 
        self._indent("br label %%%s" %(blockname,))

    def br(self, cond, blockname_false, blockname_true):
        self._indent("br bool %s, label %%%s, label %%%s"
                     % (cond, blockname_true, blockname_false))

    def switch(self, intty, cond, defaultdest, value_label):
        labels = ''
        for value, label in value_label:
            labels += ' %s %s, label %%%s' % (intty, value, label)
        self._indent("switch %s %s, label %%%s [%s ]"
                     % (intty, cond, defaultdest, labels))

    def openfunc(self, decl, cconv=DEFAULT_CCONV): 
        self.newline()
        self._append("internal %s %s {" % (cconv, decl,))

    def closefunc(self): 
        self._append("}") 

    def ret(self, type_, ref): 
        if type_ == 'void':
            self._indent("ret void")
        else:
            self._indent("ret %s %s" % (type_, ref))

    def phi(self, targetvar, type_, refs, blocknames): 
        assert len(refs) == len(blocknames), "phi node requires blocks" 
        mergelist = ", ".join(
            ["[%s, %%%s]" % item 
                for item in zip(refs, blocknames)])
        s = "%s = phi %s %s" % (targetvar, type_, mergelist)
        self._indent(s)

    def binaryop(self, name, targetvar, type_, ref1, ref2):
        self._indent("%s = %s %s %s, %s" % (targetvar, name, type_,
                                            ref1, ref2))

    def shiftop(self, name, targetvar, type_, ref1, ref2):
        self._indent("%s = %s %s %s, ubyte %s" % (targetvar, name, type_,
                                                  ref1, ref2))

    def cast(self, targetvar, fromtype, fromvar, targettype):
        if fromtype == 'void' and targettype == 'void':
            return
        self._indent("%(targetvar)s = cast %(fromtype)s "
                     "%(fromvar)s to %(targettype)s" % locals())

    # XXX refactor - should only be one getelementptr
    def raw_getelementptr(self, targetvar, type, typevar, *indices):
        word = self.word_repr
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self._indent(res)

    def getelementptr(self, targetvar, type, typevar, *indices):
        word = self.word_repr
        res = "%(targetvar)s = getelementptr " \
              "%(type)s %(typevar)s, %(word)s 0, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self._indent(res)

    def load(self, target, targettype, ptr):
        self._indent("%(target)s = load %(targettype)s* %(ptr)s" % locals())

    def store(self, valuetype, value, ptr): 
        l = "store %(valuetype)s %(value)s, %(valuetype)s* %(ptr)s" % locals()
        self._indent(l)

    def unwind(self):
        self._indent("unwind")

    def call(self, targetvar, returntype, functionref, argrefs, argtypes,
             tail=DEFAULT_TAIL, cconv=DEFAULT_CCONV):

        tail = self._resolvetail(tail, cconv)        
        args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])

        if returntype == 'void':
            self._indent("%scall %s void %s(%s)" % (tail,
                                                    cconv,
                                                    functionref,
                                                    args))
        else:
            self._indent("%s = %scall %s %s %s(%s)" % (targetvar,
                                                       tail,
                                                       cconv,
                                                       returntype,
                                                       functionref,
                                                       args))
            
