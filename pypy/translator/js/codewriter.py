import py
from itertools import count
from pypy.translator.js.log import log 

log = log.codewriter 

class CodeWriter(object): 

    tabstring = '  '

    def __init__(self, f, js): 
        self.f = f
        self.js = js

    def append(self, line, indentation_level=4): 
        if indentation_level:
            s = self.tabstring * indentation_level
        else:
            s = ''
        self.f.write(s + line + '\n')

    def comment(self, line, indentation_level=4):
        self.append("// " + line, indentation_level)

    def llvm(self, line, indentation_level=4):
        self.comment("LLVM " + line, indentation_level)

    def newline(self):
        self.append("")

    def label(self, name):
        self.append("case %d:" % name, 3)
    openblock = label

    def closeblock(self):
        self.append('break')

    def globalinstance(self, name, typeandata):
        self.llvm("%s = %s global %s" % (name, "internal", typeandata))

    def structdef(self, name, typereprs):
        self.llvm("%s = type { %s }" %(name, ", ".join(typereprs)))

    def arraydef(self, name, lentype, typerepr):
        self.llvm("%s = type { %s, [0 x %s] }" % (name, lentype, typerepr))

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.llvm("%s = type %s (%s)" % (name, rettyperepr,
                                           ", ".join(argtypereprs)))

    def declare(self, decl):
        #self.llvm("declare %s" % decl, 0)
        pass

    def startimpl(self):
        #self.llvm("implementation", 0)
        pass

    def br_uncond(self, blockname): 
        self.append('prevblock = block')
        self.append('block = %d' % blockname)
        #self.llvm("br label %s" %(blockname,))

    def br(self, cond, blockname_false, blockname_true):
        self.append('prevblock = block')
        self.append('block = %s ? %d : %d' % (cond, blockname_true, blockname_false))
        #self.llvm("br bool %s, label %s, label %s" % (cond, blockname_true, blockname_false))

    def switch(self, intty, cond, defaultdest, value_label):
        labels = ''
        for value, label in value_label:
            labels += ' %s %s, label %s' % (intty, value, label)
        self.llvm("switch %s %s, label %s [%s ]"
                    % (intty, cond, defaultdest, labels))

    def openfunc(self, decl, funcnode, blocks): 
        self.decl     = decl
        self.funcnode = funcnode
        self.blocks   = blocks
        usedvars      = {}  #XXX could probably be limited to inputvars
        for block in blocks:
            for op in block.operations:
                targetvar = self.js.db.repr_arg(op.result)
                usedvars[targetvar] = True
        self.newline()
        self.append("function %s {" % self.decl, 0)
        if usedvars:
            self.append("var %s" % ', '.join(usedvars.keys()), 1)
        self.append("var block = 0", 1)
        self.append("while (block != undefined) {", 1)
        self.append("switch (block) {", 2)

    def closefunc(self): 
        self.append("} // end of switch (block)", 2)
        self.append("} // end of while (block != undefined)", 1)
        self.append("} // end of function %s" % self.decl, 0)

    def ret(self, type_, ref): 
        if type_ == 'void':
            self.append("return")
        else:
            self.append("return " + ref)

    def phi(self, targetvar, type_, refs, blocknames): 
        assert refs and len(refs) == len(blocknames), "phi node requires blocks" 
        #mergelist = ", ".join(
        #    ["[%s, %s]" % item 
        #        for item in zip(refs, blocknames)])
        #s = "%s = phi %s %s" % (targetvar, type_, mergelist)
        #self.llvm(s)
        all_refs_identical = True
        for ref in refs:
            if ref != refs[0]:
                all_refs_identical = False
                break
        if all_refs_identical:
            if targetvar != refs[0]:
                self.append('%s = %s' % (targetvar, refs[0]))
        else:
            if len(blocknames) == 1:
                self.append('%s = %s' % (targetvar, refs[i]))
            else:
                n = 0
                for i, blockname in enumerate(blocknames):
                    if targetvar != refs[i]:
                        if n > 0:
                            s = 'else '
                        else:
                            s = ''
                        self.append('%sif (prevblock == %d) %s = %s' % (s, blockname, targetvar, refs[i]))
                        n += 1

    def binaryop(self, name, targetvar, type_, ref1, ref2):
        arithmetic = '*/+-'
        comparison = ('<', '<=', '==', '!=', '>=', '>')
        if name in arithmetic or name in comparison:
            self.append("%(targetvar)s = %(ref1)s %(name)s %(ref2)s" % locals())
        else:
            self.llvm("%s = %s %s %s, %s" % (targetvar, name, type_, ref1, ref2))

    def shiftop(self, name, targetvar, type_, ref1, ref2):
        self.llvm("%s = %s %s %s, ubyte %s" % (targetvar, name, type_, ref1, ref2))

    def call(self, targetvar, returntype, functionref, argrefs, argtypes, label=None, except_label=None):
        args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])
        if except_label:
            self.js.exceptionpolicy.invoke(self, targetvar, returntype, functionref, args, label, except_label)
        else:
            if returntype == 'void':
                self.llvm("call void %s(%s)" % (functionref, args))
            else:
                self.llvm("%s = call %s %s(%s)" % (targetvar, returntype, functionref, args))

    def cast(self, targetvar, fromtype, fromvar, targettype):
    	if fromtype == 'void' and targettype == 'void':
		return
        if targettype == fromtype:
            self.append("%(targetvar)s = %(fromvar)s%(convfunc)s" % locals())
        elif targettype in ('int','uint',):
            self.append("%(targetvar)s = Math.floor(%(fromvar)s)" % locals())
        elif targettype in ('double',):
            self.append("%(targetvar)s = 0.0 + %(fromvar)s" % locals())
        elif targettype in ('bool',):
            self.append("%(targetvar)s = %(fromvar)s == 0" % locals())
        else:
            self.llvm("%(targetvar)s = cast %(fromtype)s %(fromvar)s to %(targettype)s" % locals())

    def malloc(self, targetvar, type_, size=1, atomic=False):
        for s in self.js.gcpolicy.malloc(targetvar, type_, size, atomic, 'word', 'uword').split('\n'):
            self.llvm(s)

    def getelementptr(self, targetvar, type, typevar, *indices):
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, word 0, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self.llvm(res)

    def load(self, targetvar, targettype, ptr):
        self.llvm("%(targetvar)s = load %(targettype)s* %(ptr)s" % locals())

    def store(self, valuetype, valuevar, ptr): 
        self.llvm("store %(valuetype)s %(valuevar)s, "
                    "%(valuetype)s* %(ptr)s" % locals())

    def debugcomment(self, tempname, len, tmpname):
        res = "%s = call ccc %(word)s (sbyte*, ...)* printf(" % locals()
        res += "sbyte* getelementptr ([%s x sbyte]* %s, word 0, word 0) )" % locals()
        res = res % (tmpname, len, tmpname)
        self.llvm(res)
