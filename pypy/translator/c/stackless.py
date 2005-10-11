"""Stackless-style code generator.

This produces C source in the style that was manually experimented
with in http://codespeak.net/svn/user/arigo/hack/misc/stackless.c
"""

import py
from pypy.translator.c.funcgen import FunctionCodeGenerator


class StacklessData:

    def __init__(self):
        self.frame_types = {}
        self.globalstatecounter = 1

    def get_frame_type(self, n_integers, n_floats, n_pointers):
        key = n_integers, n_floats, n_pointers
        try:
            return self.frame_types[key]
        except KeyError:
            name = 'slp_frame_%d_%d_%d_s' % key
            self.frame_types[key] = name
            return name

    def writefiles(self, sg):
        f = sg.makefile('slp_defs.h')
        items = self.frame_types.items()
        items.sort()
        for (n_integers, n_floats, n_pointers), structname in items:
            types = (['long']*n_integers +
                     ['double']*n_floats +
                     ['void *']*n_pointers)
            varnames = (['l%d;' % i for i in range(n_integers)] +
                        ['d%d;' % i for i in range(n_floats)] +
                        ['p%d;' % i for i in range(n_pointers)])
            fields = []
            for type, varname in zip(types, varnames):
                fields.append('%s %s;' % (type, varname))
            print >> f, 'struct %s { slp_frame_t header; %s };' % (
                structname, ' '.join(fields))

            arguments = ['int state']
            saving_lines = []
            for type, varname in zip(types, varnames):
                arguments.append('%s %s' % (type, varname))
                saving_lines.append('((struct %s*) f)->%s = %s;' % (
                    structname, varname, varname))

            code = str(py.code.Source('''
                void *save_%(name)s(%(arguments)s)
                {
                    frame_t* f = new_frame(sizeof(struct %(name)s), state);
                    frame_stack_bottom->f_back = f;
                    frame_stack_bottom = f;
                    %(saving_lines)s
                    return NULL;
                }
            '''))
            print >> f, code % {'name': structname,
                                'arguments': ', '.join(arguments),
                                'saving_lines': '\n'.join(saving_lines)}

        f.close()
        f = sg.makefile('slp_signatures.h')
        ...
        f.close()
        f = sg.makefile('slp_XXX.h')
        ...
        f.close()


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
                    yield line
            yield '\t}'
            yield '\tassert(!"bad restart_substate");'
            yield '}'
        del self.savelines
        del self.resumeblocks

    def check_directcall_result(self, op, err):
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
            for v in op1:
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
        for v in vars:
            st = simplified_type(v.concretetype)
            if st is not None:   # ignore the Voids
                counts[st].append('(%s)%s' % (st, self.expr(v)))
        structname = self.get_frame_type(len(counts["long"]),
                                         len(counts["double"]),
                                         len(counts["void*"]))

        # reorder the vars according to their type
        vars = counts["long"] + counts["double"] + counts["void*"]

        # generate the 'save:' line
        label = 'save_%d' % len(self.savelines)
        arguments = ['%d' % self.globalstatecounter] + vars
        self.savelines.append('%s: return (%s) save_%s(%s);' % (
            label,
            self.lltypename(self.graph.getreturnvar()).replace('@', ''),
            structname,
            ', '.join(arguments))
        
        save_0: return (int) save_frame_1(0, n);
        

        ...
        ...


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
