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
        self.append('continue')

    def globalinstance(self, name, typeanddata):
        #self.append('%s = %s' % (name, typeanddata[1:].split('{')[1][:-1]), 0)
        lines = typeanddata.split('\n')
        #self.llvm("%s = global %s" % (name, lines[0]), 0)
        self.append("%s = %s" % (name, lines[0]), 0)
        for line in lines[1:]:
            self.llvm(line, 0)

    def structdef(self, name, typereprs):
        self.llvm("%s = type { %s }" %(name, ", ".join(typereprs)), 0)

    def arraydef(self, name, lentype, typerepr):
        self.llvm("%s = type { %s, [0 x %s] }" % (name, lentype, typerepr), 0)

    def funcdef(self, name, rettyperepr, argtypereprs):
        self.llvm("%s = type %s (%s)" % (name, rettyperepr,
                                           ", ".join(argtypereprs)), 0)

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
        self.append("%(targetvar)s = %(ref1)s %(name)s %(ref2)s" % locals())

    def neg(self, targetvar, source):
        self.append('%(targetvar)s = -%(source)s' % locals())
        
    def call(self, targetvar, returntype, functionref, argrefs, argtypes, label=None, except_label=None):
        #args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])
        args = ", ".join(argrefs)
        if except_label:
            self.js.exceptionpolicy.invoke(self, targetvar, returntype, functionref, args, label, except_label)
        else:
            if returntype == 'void':
                #self.llvm("call void %s(%s)" % (functionref, args))
                self.append('%s(%s)' % (functionref, args))
            else:
                #self.llvm("%s = call %s %s(%s)" % (targetvar, returntype, functionref, args))
                self.append('%s = %s(%s)' % (targetvar, functionref, args))

    def cast(self, targetvar, fromtype, fromvar, targettype):
        self.comment('codewriter cast 1 targettype=%(targettype)s, targetvar=%(targetvar)s, fromtype=%(fromtype)s, fromvar=%(fromvar)s' % locals())
    	if fromtype == 'void' and targettype == 'void':
		return
        self.comment('codewriter cast 2')
        if targettype == fromtype:
            self.append("%(targetvar)s = %(fromvar)s" % locals())
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
        
        #res = "%(targetvar)s = %(typevar)s" % locals()
        #res += ''.join(['[%s]' % i for t, i in indices])
        #self.append(res)

    #def load(self, targetvar, targettype, ptr):
    #    self.llvm("%(targetvar)s = load %(targettype)s* %(ptr)s" % locals())

    def load(self, destvar, src, srcindices):
        res  = "%(destvar)s = %(src)s" % locals()
        res += ''.join(['[%s]' % index for index in srcindices])
        self.append(res)

    #def store(self, valuetype, valuevar, ptr): 
    #    self.llvm("store %(valuetype)s %(valuevar)s, %(valuetype)s* %(ptr)s" % locals())

    def store(self, dest, destindices, srcvar):
        res  = dest
        res += ''.join(['[%s]' % index for index in destindices])
        res += " = %(srcvar)s" % locals()
        self.append(res)

    def debugcomment(self, tempname, len, tmpname):
        res = "%s = call %(word)s (sbyte*, ...)* printf(" % locals()
        res += "sbyte* getelementptr ([%s x sbyte]* %s, word 0, word 0) )" % locals()
        res = res % (tmpname, len, tmpname)
        self.llvm(res)
