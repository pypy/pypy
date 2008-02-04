class CodeWriter(object): 
    linkage = 'internal '       #internal/

    def __init__(self, file, db, linkage=None): 
        self.db = db
        self.file = file
        self.word_repr = db.get_machine_word()
        if linkage is not None:
            self.linkage = linkage

    def close(self): 
        self.file.close()

    # keep these two internal for now - incase we try a different API
    def _append(self, line): 
        self.file.write(line + '\n')

    def _indent(self, line): 
        self._append("        " + line) 

    def write_lines(self, lines, patch=False):
        for l in lines.split("\n"):
            if patch:
                l = l.replace('WORD', self.word_repr)
            self._append(l)
    
    def comment(self, line, indent=True):
        line = ";; " + line
        if indent:
            self._indent(line)
        else:
            self._append(line)

    def header_comment(self, s):
        self.newline()
        self.comment('=' * 78, indent=False)
        self.comment(s, indent=False)
        self.comment('=' * 78, indent=False)
        self.newline()

    def newline(self):
        self._append("")

    def label(self, name):
        self.newline()
        self._append("    %s:" % name)

    def globalinstance(self, name, typeandata, linkage=None):
        assert not typeandata.startswith('i8')
        if linkage is None:
            linkage = self.linkage
        self._append("%s = %sglobal %s" % (name, linkage, typeandata))

    def typedef(self, name, type_):
        self._append("%s = type %s" % (name, type_))

    def declare(self, decl):
        self._append("declare %s" % decl)

    def br_uncond(self, blockname): 
        self._indent("br label %%%s" %(blockname,))

    def br(self, cond, blockname_false, blockname_true):
        self._indent("br i1 %s, label %%%s, label %%%s"
                     % (cond, blockname_true, blockname_false))

    def switch(self, intty, cond, defaultdest, value_labels):
        labels = ''
        for value, label in value_labels:
            labels += ' %s %s, label %%%s' % (intty, value, label)
        self._indent("switch %s %s, label %%%s [%s ]"
                     % (intty, cond, defaultdest, labels))

    def openfunc(self, decl, linkage=None): 
        if linkage is None:
            linkage = self.linkage
        self.newline()
        self._append("define %s %s {" % (linkage, decl,))

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
        self._indent("%s = %s %s %s, %s" % (targetvar, name, type_, ref1, ref2))

    def cast(self, targetvar, fromtype, fromvar, targettype, casttype='bitcast'):
        if fromtype == 'void' and targettype == 'void':
            return
        self._indent("%(targetvar)s = %(casttype)s %(fromtype)s "
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

    def call(self, targetvar, returntype, functionref, argtypes, argrefs, ret_type_attrs=""):
        args = ", ".join(["%s %s" % item for item in zip(argtypes, argrefs)])

        if returntype == 'void':
            return_str = ''
        else:
            return_str = '%s = ' % targetvar

        self._indent("%s call %s %s(%s) %s" % (return_str,
                                               returntype,
                                               functionref,
                                               args,
                                               ret_type_attrs))

    def alloca(self, targetvar, vartype):
        self._indent("%s = alloca %s" % (targetvar, vartype))

#     def malloc(self, targetvar, vartype, numelements=1):
#         XXX # we should use this for raw malloc (unless it is slow)
#         if numelements == 1:
#             self._indent("%s = malloc %s" % (targetvar, vartype))
#         else:
#             assert numelements > 1
#             self._indent("%s = malloc %s, uint %s" % (targetvar,
#                                                       vartype,
#                                                       numelements))
            

#     def free(self, vartype, varref):
#         XXX # we should use this for raw malloc (unless it is slow)
#         self._indent("free %s %s" % (vartype, varref))

    def debug_print(self, s):
        var = self.db.repr_tmpvar()
        node = self.db.create_debug_string(s)
        arg = "bitcast(%s* %s to i8*)" % (node.get_typerepr(), node.ref)
        self.call(var, "i32", "@write",
                  ['i32', 'i8*', 'i32'],
                  ['2', arg, '%d' % node.get_length()])

    # ____________________________________________________________
    # Special support for llvm.gcroot

    def declare_gcroots(self, gcrootscount):
        assert self.db.genllvm.config.translation.gcrootfinder == "llvmgc"
        for i in range(gcrootscount):
            self._indent("%%gcroot%d = alloca i8*" % i)
        for i in range(gcrootscount):
            self._indent("call void @llvm.gcroot(i8** %%gcroot%d, i8* null)"
                         % i)
