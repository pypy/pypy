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
        self.set_indentation_level(0)

    def skip_closeblock(self, flag=True):
        self._skip_closeblock = flag

    def set_indentation_level(self, indentation_level):
        try:
            old = self.indentation_level
        except:
            old = 0
        self.indentation_level = indentation_level
        return old

    def indent_more(self):
        self.indentation_level += 1

    def indent_less(self):
        self.indentation_level -= 1

    def append(self, line): 
        if line and self.indentation_level:
            s = self.tabstring * self.indentation_level
        else:
            s = ''
        if not line or line[-1] in '{:};' or line.lstrip()[:2] == '//':
            eol = '\n'
        else:
            eol = ';\n'
        self.f.write(s + line + eol)

    def comment(self, line):
        self.append("// " + line)

    def llvm(self, line):
        self.comment("LLVM " + line)

    def newline(self):
        self.append("")

    def openblock(self, name):
        self.indent_more()
        self.append("case %d:" % name)
        self.indent_more()
        self._currentblock = name

    def closeblock(self):
        if not self._skip_closeblock:
            self.append('break')
        self.indent_less()
        self.indent_less()
        self.skip_closeblock(False)

    def globalinstance(self, lines=[]):
        for line in lines:
            self.append(line)

    def declare(self, decl):
        self.append(decl)

    def _goto_block(self, block):
        if block == self._currentblock + 1:
            self._skip_closeblock = True
        else:
            self.append('block = ' + str(block))
            self.append('break')

    def _phi(self, exit):
        for i, exitarg in enumerate(exit.args):
            dest = str(exit.target.inputargs[i])
            src = str(self.js.db.repr_arg(exitarg))
            if src == 'False':
                src = 'false'
            elif src == 'True':
                src = 'true'
            elif src == 'None':
                src = 'undefined'
            if dest != src and not dest.startswith('etype_'):
                if dest.startswith('evalue_') and src.startswith('last_exc_value_'):
                    src = 'e'   #i.e. the caught exception
                self.append('%s = %s' % (dest, src))

    def br_uncond(self, block, exit): 
        self._phi(exit)
        self._goto_block(block)
        self.skip_closeblock()

    def br(self, cond, block_false, exit_false, block_true, exit_true):
        self.append('if (%s) {' % cond)
        self.indent_more()
        self._phi(exit_true)
        self._goto_block(block_true)
        self.indent_less()
        self.append('} else {')
        self.indent_more()
        self._phi(exit_false)
        self._goto_block(block_false)
        self.indent_less()
        self.append('}')
        self.skip_closeblock()

    #def switch(self, intty, cond, defaultdest, value_label):
    #    labels = ''
    #    for value, label in value_label:
    #        labels += ' %s %s, label %s' % (intty, value, label)
    #    self.llvm("switch %s %s, label %s [%s ]"
    #                % (intty, cond, defaultdest, labels))

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
        self.append("function %s {" % self.decl)
        self.indent_more()
        if usedvars:
            self.append("var %s" % ', '.join(usedvars.keys()))
        self.append("for (var block = 0;;) {")
        self.indent_more()
        self.append("switch (block) {")

    def closefunc(self): 
        self.append("}")
        self.indent_less()
        self.append("}")
        self.indent_less()
        self.append("};")

    def ret(self, ref=''): 
        self.append("return " + ref)
        self.skip_closeblock()

    def binaryop(self, name, targetvar, ref1, ref2):
        self.append("%(targetvar)s = %(ref1)s %(name)s %(ref2)s" % locals())

    def neg(self, targetvar, source):
        self.append('%(targetvar)s = -%(source)s' % locals())
        
    def call(self, targetvar, functionref, argrefs, no_exception=None, exceptions=[]):
        args = ", ".join(argrefs)

        if not exceptions:
            assert no_exception is None
            self.append('%s = %s(%s)' % (targetvar, functionref, args))
        else:
            assert no_exception is not None
            no_exception_label, no_exception_exit = no_exception
            self.append('try {')
            self.indent_more()
            self.append('%s = %s(%s)' % (targetvar, functionref, args))
            self._phi(no_exception_exit)
            self._goto_block(no_exception_label)
            self.indent_less()
            
            self.append('} catch (e) {')
            self.indent_more()
            catch_all = False
            for i, exception in enumerate(exceptions):
                exception_match, exception_ref, exception_target, exit = exception
                if i:
                    else_ = 'else '
                else:
                    else_ = ''
                if exception_ref.startswith('structinstance_object_vtable'):
                    catch_all = True
                    matcher   = ''
                else:
                    matcher   = 'if (%s(e.typeptr, %s) == true) ' % (exception_match, exception_ref)
                self.append('%s%s{' % (else_, matcher))
                self.indent_more()
                self._phi(exit)
                self._goto_block(exception_target)
                self.indent_less()
                self.append('}')
            if not catch_all:
                self.append('else {')
                self.indent_more()
                self.throw('e') #reraise exception when not caught above
                self.indent_less()
                self.append('}')

            self.indent_less()
            self.append('}')

    def cast(self, targetvar, fromtype, fromvar, targettype):
        if fromtype == 'void' and targettype == 'void':
                return
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

    def malloc(self, targetvar, type_):
        self.append('%(targetvar)s = new %(type_)s()' % locals())

    def getelementptr(self, targetvar, type, typevar, *indices):
        res = "%(targetvar)s = getelementptr %(type)s %(typevar)s, word 0, " % locals()
        res += ", ".join(["%s %s" % (t, i) for t, i in indices])
        self.llvm(res)

        #res = "%(targetvar)s = %(typevar)s" % locals()
        #res += ''.join(['[%s]' % i for t, i in indices])
        #self.append(res)

    def load(self, destvar, src, srcindices):
        res  = "%(destvar)s = %(src)s" % locals()
        res += ''.join(['[%s]' % index for index in srcindices])
        self.append(res)

    def store(self, dest, destindices, srcvar):
        res  = dest
        res += ''.join(['[%s]' % index for index in destindices])
        res += " = %(srcvar)s" % locals()
        self.append(res)

    def throw(self, exc):
        self.append('throw ' + exc)
