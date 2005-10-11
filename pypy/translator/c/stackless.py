"""Stackless-style code generator.

This produces C source in the style that was manually experimented
with in http://codespeak.net/svn/user/arigo/hack/misc/stackless.c
"""

import py
from pypy.objspace.flow.model import Variable
from pypy.rpython import lltype
from pypy.rpython.memory.lladdress import Address
from pypy.translator.c.funcgen import FunctionCodeGenerator


class StacklessData:

    def __init__(self):
        self.frame_types = {}
        self.globalstatecounter = 1
        self.allsignatures = {}
        self.decode_table = []
        # start the decoding table with entries for the functions that
        # are written manually in ll_stackless.h
        self.registerunwindable('LL_stackless_stack_frames_depth',
                                lltype.FuncType([], lltype.Signed),
                                resume_points=1)

    def registerunwindable(self, functionname, FUNC, resume_points):
        if resume_points >= 1:
            try:
                signum = self.allsignatures[FUNC]
            except KeyError:
                signum = len(self.allsignatures)
                self.allsignatures[FUNC] = signum
            self.decode_table.append((functionname, signum))
            for n in range(1, resume_points):
                self.decode_table.append(('NULL', n))

    def get_frame_type(self, n_integers, n_floats, n_pointers):
        key = n_integers, n_floats, n_pointers
        try:
            return self.frame_types[key]
        except KeyError:
            name = 'slp_frame_%d_%d_%d_s' % key
            self.frame_types[key] = name
            return name

    def writefiles(self, sg):
        # generate slp_defs.h
        fi = sg.makefile('slp_defs.h')
        cname = 'slp_impl.c'
        assert sg.uniquecname(cname) == cname
        fc = sg.makefile(cname)
        print >> fc, '#define PYPY_NOT_MAIN_FILE'
        print >> fc, '#include "common_header.h"'
        for line in sg.preimpl:
            print >> fc, line
        print >> fc, '#include "src/g_include.h"'
        items = self.frame_types.items()
        items.sort()
        for (n_integers, n_floats, n_pointers), structname in items:
            types = (['long']*n_integers +
                     ['double']*n_floats +
                     ['void *']*n_pointers)
            varnames = (['l%d' % i for i in range(n_integers)] +
                        ['d%d' % i for i in range(n_floats)] +
                        ['v%d' % i for i in range(n_pointers)])
            fields = []
            for type, varname in zip(types, varnames):
                fields.append('%s %s;' % (type, varname))
            print >> fi, 'struct %s { slp_frame_t header; %s };' % (
                structname, ' '.join(fields))

            arguments = ['int state']
            saving_lines = []
            for type, varname in zip(types, varnames):
                arguments.append('%s %s' % (type, varname))
                saving_lines.append('((struct %s*) f)->%s = %s;' % (
                    structname, varname, varname))

            head = 'void *save_%(name)s(%(arguments)s);'
            code = str(py.code.Source('''
             void *save_%(name)s(%(arguments)s)
             {
                 slp_frame_t* f = slp_new_frame(sizeof(struct %(name)s), state);
                 slp_frame_stack_bottom->f_back = f;
                 slp_frame_stack_bottom = f;
                 %(saving_lines)s
                 return NULL;
             }
            '''))
            argdict = {'name': structname,
                       'arguments': ', '.join(arguments),
                       'saving_lines': '\n    '.join(saving_lines)}
            print >> fi, head % argdict
            print >> fc, code % argdict
        fi.close()
        fc.close()

        # generate slp_signatures.h
        fi = sg.makefile('slp_signatures.h')
        items = [(num, FUNC) for (FUNC, num) in self.allsignatures.items()]
        items.sort()
        for num, FUNC in items:
            # 'FUNC' is a lltype.FuncType instance
            print >> fi, 'case %d:' % num
            # XXX '0' is hopefully fine for a dummy value of any type
            #     for most compilers
            dummyargs = ['0'] * len(FUNC.ARGS)
            callexpr = '((%s) fn) (%s);' % (
                sg.database.gettype(lltype.Ptr(FUNC)).replace('@', ''),
                ', '.join(dummyargs))
            globalretvalvartype = simplified_type(FUNC.RESULT)
            if globalretvalvartype is not None:
                globalretvalvarname = RETVALVARS[globalretvalvartype]
                callexpr = '%s = (%s) %s' % (globalretvalvarname,
                                             globalretvalvartype,
                                             callexpr)
            print >> fi, '\t' + callexpr
            print >> fi, '\tbreak;'
            print >> fi
        fi.close()

        # generate slp_state_decoding.h
        fi = sg.makefile('slp_state_decoding.h')
        print >> fi, 'static struct slp_state_decoding_entry_s',
        print >> fi, 'slp_state_decoding_table[] = {'
        for i, (functionname, signum) in enumerate(self.decode_table):
            print >> fi, '/* %d */ { %s, %d },' % (i, functionname, signum)
        print >> fi, '};'
        fi.close()


class SlpFunctionCodeGenerator(FunctionCodeGenerator):

    def cfunction_body(self):
        # lists filled by check_directcall_result() from super.cfunction_body()
        self.savelines = []
        self.resumeblocks = []
        body = list(super(SlpFunctionCodeGenerator, self).cfunction_body())
        #
        if self.savelines:   # header (if we need to resume)
            yield 'if (slp_frame_stack_top) goto resume;'
        for line in body:    # regular body
            yield line
        if self.savelines:
            yield ''
            for line in self.savelines:  # save-state-away lines
                yield line
            yield ''
            yield 'resume:'    # resume-state blocks
            yield '{'
            yield '\tslp_frame_t* f = slp_frame_stack_top;'
            yield '\tslp_frame_stack_top = NULL;'
            yield '\tswitch (slp_restart_substate) {'
            for block in self.resumeblocks:
                for line in block:
                    yield '\t'+line
            yield '\t}'
            yield '\tassert(!"bad restart_substate");'
            yield '}'
            
            # record extra data needed to generate the slp_*.h tables:
            # find the signatures of all functions
            slpdata = self.db.stacklessdata
            argtypes = [erase_ptr_type(v.concretetype)
                        for v in self.graph.getargs()]
            argtypes = [T for T in argtypes if T is not lltype.Void]
            rettype = erase_ptr_type(self.graph.getreturnvar().concretetype)
            FUNC = lltype.FuncType(argtypes, rettype)
            slpdata.registerunwindable(self.functionname, FUNC,
                                       resume_points = len(self.resumeblocks))

        del self.savelines
        del self.resumeblocks

    def check_directcall_result(self, op, err):
        stacklessdata = self.db.stacklessdata
        block = self.currentblock
        curpos = block.operations.index(op)

        # XXX obscure: find all variables that are produced before 'op'
        # and still used by or after 'op'.
        produced = {}
        for v in block.inputargs:
            produced[v] = True
        for op1 in block.operations[:curpos]:
            produced[op1.result] = True
        consumed = {}
        for op1 in block.operations[curpos:]:
            for v in op1.args:
                if isinstance(v, Variable):
                    consumed[v] = True
        if isinstance(block.exitswitch, Variable):
            consumed[block.exitswitch] = True
        for link in block.exits:
            for v in link.args:
                if isinstance(v, Variable):
                    consumed[v] = True
        vars = [v for v in produced if v in consumed]

        # get the simplified frame struct that can store these vars
        counts = {"long":   [],
                  "double": [],
                  "void*":  []}
        variables_to_restore = []
        for v in vars:
            st = simplified_type(v.concretetype)
            if st is not None:   # ignore the Voids
                varname = self.expr(v)
                # XXX hackish: the name of the field in the structure is
                # computed from the 1st letter of the 'st' type, counting
                # from 0 for each of the 'st' types independently
                variables_to_restore.append((v, '%s%d' % (
                    st[0], len(counts[st]))))
                counts[st].append('(%s)%s' % (st, varname))
        structname = stacklessdata.get_frame_type(len(counts["long"]),
                                                  len(counts["double"]),
                                                  len(counts["void*"]))

        # reorder the vars according to their type
        vars = counts["long"] + counts["double"] + counts["void*"]

        # generate the 'save:' line, e.g.
        #      save_0: return (int) save_frame_1(0, (long) n);
        savelabel = 'save_%d' % len(self.savelines)
        arguments = ['%d' % stacklessdata.globalstatecounter] + vars
        stacklessdata.globalstatecounter += 1
        savecall = 'save_%s(%s);' % (structname, ', '.join(arguments))
        retvar = self.graph.getreturnvar()
        if retvar.concretetype is lltype.Void:
            savecall += ' return;'
        else:
            savecall = 'return (%s) %s' % (
                self.lltypename(retvar).replace('@', ''),
                savecall)
        self.savelines.append('%s: %s' % (savelabel, savecall))

        # generate the resume block, e.g.
        #        case 1:
        #          n = (long)(((struct frame_1_s*) f)->i1);
        #          b = (long) retval_long;
        #          goto resume_1;
        resumelabel = 'resume_%d' % len(self.resumeblocks)
        lines = ['case %d:' % len(self.resumeblocks)]
        for v, fieldname in variables_to_restore:
            varname = self.expr(v)
            vartype = self.lltypename(v).replace('@', '')
            lines.append('%s = (%s)(((struct %s*) f)->%s);' % (
                varname, vartype, structname, fieldname))
        retvarname = self.expr(op.result)
        retvartype = self.lltypename(op.result).replace('@', '')
        retvarst = simplified_type(op.result.concretetype)
        if retvarst is not None:
            globalretvalvarname = RETVALVARS[retvarst]
            lines.append('%s = (%s) %s;' % (
                retvarname, retvartype, globalretvalvarname))
        lines.append('goto %s;' % (resumelabel,))
        self.resumeblocks.append(lines)

        # add the checks for the unwinding case just after the directcall
        # in the source
        unwind_check = "if (slp_frame_stack_bottom) goto %s;" % (savelabel,)
        exception_check = (super(SlpFunctionCodeGenerator, self)
                           .check_directcall_result(op, err))
        return '%s\n     %s:\n\t%s' % (unwind_check,
                                       resumelabel,
                                       exception_check)


def erase_ptr_type(T):
    """Return T unless it's a pointer type, in which case we return a general
    basic pointer type.
    """
    if isinstance(T, lltype.Ptr):
        return Address
    else:
        return T


def simplified_type(T):
    if T is lltype.Void:
        return None
    elif T is lltype.Float:
        return "double"
    elif isinstance(T, lltype.Primitive):
        return "long"   # large enough for all other primitives
    elif isinstance(T, lltype.Ptr):
        return "void*"
    else:
        raise Exception("don't know about %r" % (T,))

RETVALVARS = {
    "double": "slp_retval_double",
    "long"  : "slp_retval_long",
    "void*" : "slp_retval_voidptr",
    }
