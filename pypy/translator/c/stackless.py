"""Stackless-style code generator.

This produces C source in the style that was manually experimented
with in http://codespeak.net/svn/user/arigo/hack/misc/stackless.c
"""

import py
from pypy.objspace.flow.model import Variable
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.memory.lladdress import Address
from pypy.translator.c.support import cdecl
from pypy.translator.c.funcgen import FunctionCodeGenerator

class StacklessData:

    def __init__(self, database):
        self.frame_types = {}
        self.allsignatures = {}
        self.decode_table = []
        self.stackless_roots = {}

        # start the decoding table with entries for the functions that
        # are written manually in ll_stackless.h
        def reg(name):
            self.stackless_roots[name.lower()] = True
            return name

        reg('LL_stack_unwind')
        self.registerunwindable(reg('LL_stackless_stack_unwind'),
                                lltype.FuncType([], lltype.Void),
                                resume_points=1)
        self.registerunwindable(reg('LL_stackless_stack_frames_depth'),
                                lltype.FuncType([], lltype.Signed),
                                resume_points=1)
        self.registerunwindable(reg('LL_stackless_switch'),
                                lltype.FuncType([Address], Address),
                                resume_points=1)
        self.registerunwindable(reg('slp_end_of_yielding_function'),
                                lltype.FuncType([], Address),
                                resume_points=1)

        self.can_reach_unwind = {}
        self.database = database
        self.count_calls = [0, 0]

    def unwind_reachable(self, func):
        reach_dict = self.can_reach_unwind
        if func not in reach_dict:
            self.setup()
        return reach_dict[func]

    def setup(self):
        # to be called after database is complete, or we would
        # not have valid externals info
        self._compute_reach_unwind()

    def _compute_reach_unwind(self):
        callers = {}
        assert self.database.completed
        translator = self.database.translator
        here = len(translator.functions)
        for func in translator.functions:
            callers[func] = []
        for caller, callee in translator.complete_callgraph.values():
            callers[caller].append(callee)
        # add newly generated ones
        for func in translator.functions[here:]:
            callers.setdefault(func, [])
        # check all callees if they can reach unwind
        seen = self.can_reach_unwind
        
        pending = {}
        ext = self.database.externalfuncs
        def check_unwind(func):
            if func in pending:
                ret = func not in ext
                # typical pseudo-recursion of externals
                # but true recursions do unwind
                seen[func] = ret
                return ret
            pending[func] = func
            for callee in callers[func]:
                if callee in seen:
                    ret = seen[callee]
                else:
                    ret = check_unwind(callee)
                if ret:
                    break
            else:
                ret = func.__name__ in self.stackless_roots
            del pending[func]
            seen[func] = ret
            return ret
        [check_unwind(caller) for caller in callers if caller not in seen]

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

    def get_frame_type(self, counts):
        """Return the frame struct name,
        named after the number of saved variables of each kind.
        counts is a sequence of numbers, ordered like STATE_TYPES
        """
        key = tuple(counts)
        try:
            return self.frame_types[key]
        except KeyError:
            nums = "_".join([str(c) for c in key])
            name = 'slp_frame_%s_s' % nums
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
        for counts, structname in items:
            varnames = []
            for count, vartype in zip(counts, STATE_TYPES):
                varnames.extend([(vartype.ctype, '%s%d' % (vartype.prefix, i))
                                 for i in range(count)])

            # generate the struct definition
            fields = []
            for type, varname in varnames:
                fields.append('%s %s;' % (type, varname))
            print >> fi, 'struct %s { slp_frame_t header; %s };' % (
                structname, ' '.join(fields))

            # generate the 'save_' function
            arguments = ['int state']
            saving_lines = []
            for type, varname in varnames:
                arguments.append('%s %s' % (type, varname))
                saving_lines.append('((struct %s*) f)->%s = %s;' % (
                    structname, varname, varname))

            head = 'void save_%(name)s(%(arguments)s);'
            code = str(py.code.Source('''
             void save_%(name)s(%(arguments)s)
             {
                 slp_frame_t* f = slp_new_frame(sizeof(struct %(name)s), state);
                 slp_frame_stack_bottom->f_back = f;
                 slp_frame_stack_bottom = f;
                 %(saving_lines)s
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
            functiontype = sg.database.gettype(lltype.Ptr(FUNC))
            callexpr = '((%s) fn) (%s);' % (cdecl(functiontype, ''),
                                            ', '.join(dummyargs))
            globalretvalvartype = storage_type(FUNC.RESULT)
            if globalretvalvartype is not None:
                callexpr = '%s = (%s) %s' % (globalretvalvartype.global_name,
                                             globalretvalvartype.ctype,
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
            argtypes = [signature_type(self.lltypemap(v))
                        for v in self.graph.getargs()]
            argtypes = [T for T in argtypes if T is not lltype.Void]
            rettype = signature_type(self.lltypemap(self.graph.getreturnvar()))
            FUNC = lltype.FuncType(argtypes, rettype)
            slpdata.registerunwindable(self.functionname, FUNC,
                                       resume_points = len(self.resumeblocks))

        del self.savelines
        del self.resumeblocks

    def check_directcall_result(self, op, err, specialreturnvalue=None):
        slp = self.db.stacklessdata
        # don't generate code for calls that cannot unwind
        if not specialreturnvalue:
            need_stackless = slp.unwind_reachable(self.graph.func)
            if need_stackless:
                try:
                    callee = op.args[0].value._obj.graph.func
                except AttributeError:
                    pass # assume we need it really
                else:
                    need_stackless = slp.unwind_reachable(callee)
            if not need_stackless:
                slp.count_calls[False] += 1
                return (super(SlpFunctionCodeGenerator, self)
                        .check_directcall_result(op, err))
        slp.count_calls[True] += 1
        block = self.currentblock
        curpos = block.operations.index(op)
        vars = list(variables_to_save_across_op(block, curpos))

        # get the simplified frame struct that can store these vars
        counts = dict([(type, []) for type in STATE_TYPES])
        variables_to_restore = []
        for v in vars:
            st = storage_type(self.lltypemap(v))
            if st is not None:   # ignore the Voids
                varname = self.expr(v)
                # The name of the field in the structure is computed from
                # the prefix of the 'st' type, counting from 0 for each
                # of the 'st' types independently
                variables_to_restore.append((v, '%s%d' % (
                    st.prefix, len(counts[st]))))
                counts[st].append('(%s)%s' % (st.ctype, varname))
        structname = slp.get_frame_type([len(counts[st]) for st in STATE_TYPES])

        # reorder the vars according to their type
        vars = sum([counts[st] for st in STATE_TYPES],[])

        # generate the 'save:' line, e.g.
        #      save_0: return (int) save_frame_1(0, (long) n);
        savelabel = 'save_%d' % len(self.savelines)

        # The globally unique number for our state
        # is the total number of saved states so far
        globalstatecounter = len(slp.decode_table) + len(self.savelines)
        
        arguments = ['%d' % globalstatecounter] + vars

        savecall = 'save_%s(%s);' % (structname, ', '.join(arguments))
        returnvalue = specialreturnvalue or self.error_return_value()
        savecall += ' return %s;' % returnvalue
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
            vartype = self.lltypename(v)
            lines.append('%s = (%s)(((struct %s*) f)->%s);' % (
                varname, cdecl(vartype, ''), structname, fieldname))
        retvarname = self.expr(op.result)
        retvartype = self.lltypename(op.result)
        retvarst = storage_type(self.lltypemap(op.result))
        if retvarst is not None:
            globalretvalvarname = retvarst.global_name
            lines.append('%s = (%s) %s;' % (
                retvarname, cdecl(retvartype, ''), globalretvalvarname))
        lines.append('goto %s;' % (resumelabel,))
        self.resumeblocks.append(lines)

        # add the checks for the unwinding case just after the directcall
        # in the source
        unwind_check = "if (slp_frame_stack_bottom)\n\tgoto %s;" % (savelabel,)
        exception_check = (super(SlpFunctionCodeGenerator, self)
                           .check_directcall_result(op, err))
        return '%s\n  %s:\n%s' % (unwind_check,
                                    resumelabel,
                                    exception_check)

    def OP_YIELD_CURRENT_FRAME_TO_CALLER(self, op, err):
        # special handling of this operation: call stack_unwind() to force the
        # current frame to be saved into the heap, but don't propagate the
        # unwind -- instead, capture it and return it normally
        line = '/* yield_current_frame_to_caller */\n'
        line += '%s = NULL;\n' % self.expr(op.result)
        line += 'LL_stackless_stack_unwind();\n'
        line += self.check_directcall_result(op, err,
                    specialreturnvalue='slp_return_current_frame_to_caller()')
        return line


def signature_type(T):
    """Return T unless it's a pointer type, in which case we return a general
    basic pointer type.
    The returned type must have the same behaviour when put on the C stack.
    """
    if isinstance(T, lltype.Ptr):
        return Address
    else:
        return T


class StateVariableType:
    def __init__(self, ctype, prefix, global_name):
        self.ctype = ctype
        self.prefix = prefix
        self.global_name = global_name

STATE_TYPES = [
    StateVariableType('long',   'l', 'slp_retval_long'),
    StateVariableType('void*',  'p', 'slp_retval_voidptr'),
    StateVariableType('double', 'd', 'slp_retval_double'),
    ]

def storage_type(T):
    """Return the type used to save values of this type
    """
    if T is lltype.Void:
        return None
    elif T is lltype.Float:
        return STATE_TYPES[ 2 ]
    elif T is Address or isinstance(T, lltype.Ptr):
        return STATE_TYPES[ 1 ]
    elif isinstance(T, lltype.Primitive):
        return STATE_TYPES[ 0 ] # long is large enough for all other primitives
    else:
        raise Exception("don't know about %r" % (T,))

def variables_to_save_across_op(block, opindex):
    # variable lifetime detection:
    # 1) find all variables that are produced before the operation
    produced = {}
    for v in block.inputargs:
        produced[v] = True
    for op1 in block.operations[:opindex]:
        produced[op1.result] = True
    # 2) find all variables that are used by or after the operation
    consumed = {}
    for op1 in block.operations[opindex:]:
        for v in op1.args:
            if isinstance(v, Variable):
                consumed[v] = True
    if isinstance(block.exitswitch, Variable):
        consumed[block.exitswitch] = True
    for link in block.exits:
        for v in link.args:
            if isinstance(v, Variable):
                consumed[v] = True
    # 3) variables that are atomic and not consumed after the operation
    #    don't have to have their lifetime extended; that leaves only
    #    the ones that are not atomic or consumed.
    for v in produced:
        if v in consumed or not v.concretetype._is_atomic():
            yield v
