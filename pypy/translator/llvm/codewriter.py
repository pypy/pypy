from pypy.translator.llvm.log import log 
from pypy.translator.llvm.buildllvm import postfix

log = log.codewriter 

class CodeWriter(object): 
    tail = ''       #/tail
    cconv = 'fastcc'    #ccc/fastcc
    linkage = 'internal '       #/internal (disabled for now because of the JIT)

    def __init__(self, file, db, tail=None, cconv=None, linkage=None): 
        self.file = file
        self.word_repr = db.get_machine_word()
        self.uword_repr = db.get_machine_uword()
        if tail is not None:
            self.tail = tail
        if cconv is not None:
            self.cconv = cconv
        if linkage is not None:
            self.linkage = linkage

    def close(self): 
        self.file.close()

    def _resolvetail(self, tail, cconv):
        # from: http://llvm.org/docs/LangRef.html
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

    def write_lines(self, lines, patch=False):
        for l in lines.split("\n"):
            if patch:
                l = l.replace('UWORD', self.uword_repr)
                l = l.replace('WORD', self.word_repr)
                l = l.replace('POSTFIX', postfix())
                l = l.replace('CC', self.cconv)
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

    def globalinstance(self, name, typeandata, linkage=None):
        if linkage is None:
            linkage = self.linkage
        self._append("%s = %sglobal %s" % (name, linkage, typeandata))

    def typedef(self, name, type_):
        self._append("%s = type %s" % (name, type_))

    def declare(self, decl, cconv=None):
        if cconv is None:
            cconv = self.cconv
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

    def switch(self, intty, cond, defaultdest, value_labels):
        labels = ''
        for value, label in value_labels:
            labels += ' %s %s, label %%%s' % (intty, value, label)
        self._indent("switch %s %s, label %%%s [%s ]"
                     % (intty, cond, defaultdest, labels))

    def openfunc(self, decl, cconv=None, linkage=None): 
        if cconv is None:
            cconv = self.cconv
        if linkage is None:
            linkage = self.linkage
        self.newline()
        self._append("%s%s %s {" % (linkage, cconv, decl,))

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

    def getelementptr(self, targetvar, type, typevar, indices, getptr=True):
        # getelementptr gives you back a value for the last thing indexed

        # what is getptr?
        # ---------------
        # All global variables in LLVM are pointers, and pointers must also be
        # dereferenced with the getelementptr instruction (hence the int 0)

        # not only that, but if we need to look into something (ie a struct)
        # then we must get the initial pointer to ourself

        if getptr:
            indices = [(self.word_repr, 0)] + list(indices)
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self._indent(res)

    def load(self, target, targettype, ptr):
        self._indent("%(target)s = load %(targettype)s* %(ptr)s" % locals())

    def store(self, valuetype, value, ptr): 
        l = "store %(valuetype)s %(value)s, %(valuetype)s* %(ptr)s" % locals()
        self._indent(l)

    def unwind(self):
        self._indent("unwind")

    def call(self, targetvar, returntype, functionref, argtypes, argrefs,
             tail=None, cconv=None):
        if tail is None:
            tail = self.tail
        if cconv is None:
            cconv = self.cconv
            
        tail = self._resolvetail(tail, cconv)        
        args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])

        if returntype == 'void':
            return_str = ''
        else:
            return_str = '%s = ' % targetvar

        self._indent("%s%scall %s %s %s(%s)" % (return_str,
                                                tail,
                                                cconv,
                                                returntype,
                                                functionref,
                                                args))

    def alloca(self, targetvar, vartype):
        self._indent("%s = alloca %s" % (targetvar, vartype))

    def malloc(self, targetvar, vartype, numelements=1):
        if numelements == 1:
            self._indent("%s = malloc %s" % (targetvar, vartype))
        else:
            assert numelements > 1
            self._indent("%s = malloc %s, uint %s" % (targetvar,
                                                      vartype,
                                                      numelements))
            

    def free(self, vartype, varref):
        self._indent("free %s %s" % (vartype, varref))
