import py
from itertools import count
from pypy.translator.js.log import log 

log = log.codewriter 

class CodeWriter(object): 

    tabstring = '  '

    def __init__(self, f, js): 
        self.f = f
        self.js = js
        self._skip_closeblock = False

    def append(self, line, indentation_level=4): 
        if indentation_level:
            s = self.tabstring * indentation_level
        else:
            s = ''
        if not line or line[-1] in '{:};' or line.lstrip()[:2] == '//':
            eol = '\n'
        else:
            eol = ';\n'
        self.f.write(s + line + eol)

    def comment(self, line, indentation_level=4):
        self.append("// " + line, indentation_level)

    def llvm(self, line, indentation_level=4):
        self.comment("LLVM " + line, indentation_level)

    def newline(self):
        self.append("")

    def label(self, name):
        self.append("case %d:" % name, 3)

    def openblock(self, name):
        self.append("case %d:" % name, 3)
        self._currentblock = name

    def closeblock(self):
        if not self._skip_closeblock:
            self.append('break')
        self._skip_closeblock = False

    def globalinstance(self, name, typeanddata):
        #self.append('%s = %s' % (name, typeanddata[1:].split('{')[1][:-1]), 0)
        lines = typeanddata.split('\n')
        #self.llvm("%s = global %s" % (name, lines[0]), 0)
        self.append("%s = %s" % (name, lines[0]), 0)
        for line in lines[1:]:
            self.llvm(line, 0)

    def structdef(self, name, typereprs):
        #self.llvm("%s = type { %s }" %(name, ", ".join(typereprs)), 0)
        pass

    def arraydef(self, name, lentype, typerepr):
        #self.llvm("%s = type { %s, [0 x %s] }" % (name, lentype, typerepr), 0)
        pass

    def funcdef(self, name, rettyperepr, argtypereprs):
        #self.llvm("%s = type %s (%s)" % (name, rettyperepr,
        #                                   ", ".join(argtypereprs)), 0)
        pass

    def declare(self, decl):
        self.append(decl, 0)

    def startimpl(self):
        #self.llvm("implementation", 0)
        pass

    def _goto_block(self, block, indentation_level=4):
        if block == self._currentblock + 1:
            self._skip_closeblock = True
        else:
            self.append('block = ' + str(block), indentation_level)
            self.append('break', indentation_level)

    def _phi(self, targetblock, exit, indentation_level=4):
        #self.comment('target.inputargs=%s, args=%s, targetblock=%d' % (exit.target.inputargs, exit.args, targetblock), indentation_level)
        for i, exitarg in enumerate(exit.args):
            dest = str(exit.target.inputargs[i])
            #src = str(exitarg)
            src = str(self.js.db.repr_arg(exitarg))
            if src == 'False':
                src = 'false'
            elif src == 'True':
                src = 'true'
            elif src == 'None':
                src = 'undefined'
            if dest != src:
                self.append('%s = %s' % (dest, src), indentation_level)

    def br_uncond(self, block, exit): 
        self._phi(block, exit)
        self._goto_block(block)
        self._skip_closeblock = True

    def br(self, cond, block_false, exit_false, block_true, exit_true):
        self.append('if (%s) {' % cond)
        self._phi(block_true, exit_true, 5)
        self._goto_block(block_true, 5)
        self.append('} else {')
        self._phi(block_false, exit_false, 5)
        self._goto_block(block_false, 5)
        self.append('}')
        self._skip_closeblock = True

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
            if block != blocks[0]:  #don't double startblock inputargs
                for inputarg in block.inputargs:
                    targetvar = self.js.db.repr_arg(inputarg)
                    usedvars[targetvar] = True
            for op in block.operations:
                targetvar = self.js.db.repr_arg(op.result)
                usedvars[targetvar] = True
        self.newline()
        self.append("function %s {" % self.decl, 0)
        if usedvars:
            self.append("var %s" % ', '.join(usedvars.keys()), 1)
        self.append("for (var block = 0;;) {", 1)
        self.append("switch (block) {", 2)

    def closefunc(self): 
        self.append("}", 2)
        self.append("}", 1)
        self.append("};", 0)

    def ret(self, type_, ref): 
        if type_ == 'void':
            self.append("return")
        else:
            self.append("return " + ref)
        self._skip_closeblock = True

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
        #self.comment('codewriter cast 1 targettype=%(targettype)s, targetvar=%(targetvar)s, fromtype=%(fromtype)s, fromvar=%(fromvar)s' % locals())
    	if fromtype == 'void' and targettype == 'void':
		return
        #self.comment('codewriter cast 2')
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
