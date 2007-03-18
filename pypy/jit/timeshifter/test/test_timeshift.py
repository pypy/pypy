import py
import sys
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.annotator import StopAtXPolicy
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.jit.hintannotator.model import *
from pypy.jit.timeshifter.hrtyper import HintRTyper, originalconcretetype
from pypy.jit.timeshifter import rtimeshift, rvalue
from pypy.objspace.flow.model import summary, Variable
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rlib.objectmodel import hint, keepalive_until_here, debug_assert
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.annlowlevel import PseudoHighLevelCallable
from pypy.rpython.module.support import LLSupport
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter, LLException
from pypy.translator.backendopt.inline import auto_inlining
from pypy import conftest
from pypy.jit.conftest import Benchmark
from pypy.jit.codegen.llgraph.rgenop import RGenOp as LLRGenOp

P_NOVIRTUAL = HintAnnotatorPolicy(novirtualcontainer=True)

def getargtypes(annotator, values):
    return [annotation(annotator, x) for x in values]

def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

def hannotate(func, values, policy=None, inline=None, backendoptimize=False,
              portal=None):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    argtypes = getargtypes(a, values)
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    if inline:
        auto_inlining(t, threshold=inline)
    if backendoptimize:
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t)
    if portal is None:
        portal = func
    graph1 = graphof(t, portal)
    # build hint annotator types
    hannotator = HintAnnotator(base_translator=t, policy=policy)
    hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                {OriginFlags(): True})
                                         for v in graph1.getargs()])
    hannotator.simplify()
    if conftest.option.view:
        hannotator.translator.view()
    return hs, hannotator, rtyper

class TimeshiftingTests(object):
    RGenOp = LLRGenOp

    small = True

    def setup_class(cls):
        from pypy.jit.timeshifter.test.conftest import option
        cls.on_llgraph = cls.RGenOp is LLRGenOp
        if option.use_dump_backend:
            from pypy.jit.codegen.dump.rgenop import RDumpGenOp
            cls.RGenOp = RDumpGenOp
        cls._cache = {}
        cls._cache_order = []

    def teardown_class(cls):
        del cls._cache
        del cls._cache_order

    def timeshift_cached(self, ll_function, values, inline=None, policy=None,
                         check_raises='ignored anyway',
                         backendoptimize=False):
        # decode the 'values' if they are specified as strings
        if hasattr(ll_function, 'convert_arguments'):
            assert len(ll_function.convert_arguments) == len(values)
            values = [decoder(value) for decoder, value in zip(
                                        ll_function.convert_arguments, values)]

        key = ll_function, inline, policy
        try:
            cache, argtypes = self._cache[key]
        except KeyError:
            pass
        else:
            self.__dict__.update(cache)
            assert argtypes == getargtypes(self.rtyper.annotator, values)
            return values

        if len(self._cache_order) >= 3:
            del self._cache[self._cache_order.pop(0)]
        hs, ha, rtyper = hannotate(ll_function, values,
                                   inline=inline, policy=policy,
                                   backendoptimize=backendoptimize)

        # make the timeshifted graphs
        hrtyper = HintRTyper(ha, rtyper, self.RGenOp)
        hrtyper.specialize(view = conftest.option.view and self.small,
                           dont_simplify_again = True)
        fresh_jitstate = hrtyper.ll_fresh_jitstate
        finish_jitstate = hrtyper.ll_finish_jitstate
        exceptiondesc = hrtyper.exceptiondesc
        t = rtyper.annotator.translator

        # make an interface to the timeshifted graphs:
        #
        #  - a green input arg in the timeshifted entry point
        #    must be provided as a value in 'args'
        #
        #  - a redbox input arg in the timeshifted entry point must
        #    be provided as two entries in 'args': a boolean flag
        #    (True=constant, False=variable) and a value
        #
        graph1 = ha.translator.graphs[0]   # the timeshifted entry point
        assert len(graph1.getargs()) == 1 + len(values)
        graph1varargs = graph1.getargs()[1:]
        timeshifted_entrypoint_args_s = []
        argcolors = []
        generate_code_args_s = []

        for v, llvalue in zip(graph1varargs, values):
            s_var = annmodel.ll_to_annotation(llvalue)
            r = hrtyper.bindingrepr(v)
            residual_v = r.residual_values(llvalue)
            if len(residual_v) == 0:
                color = "green"
                timeshifted_entrypoint_args_s.append(s_var)
            else:
                color = "red"
                assert residual_v == [llvalue], "XXX for now"
                timeshifted_entrypoint_args_s.append(hrtyper.s_RedBox)
                generate_code_args_s.append(annmodel.SomeBool())
            argcolors.append(color)
            generate_code_args_s.append(s_var)

        timeshifted_entrypoint_fnptr = rtyper.type_system.getcallable(
            graph1)
        timeshifted_entrypoint = PseudoHighLevelCallable(
            timeshifted_entrypoint_fnptr,
            [hrtyper.s_JITState]
            + timeshifted_entrypoint_args_s,
            hrtyper.s_JITState)
        FUNC = hrtyper.get_residual_functype(ha.translator.graphs[0])
        argcolors = unrolling_iterable(argcolors)
        self.argcolors = argcolors

        def ml_generate_code(rgenop, *args):
            timeshifted_entrypoint_args = ()

            sigtoken = rgenop.sigToken(FUNC)
            builder, gv_generated, inputargs_gv = rgenop.newgraph(sigtoken,
                                                                  "generated")
            builder.start_writing()
            i = 0
            for color in argcolors:
                if color == "green":
                    llvalue = args[0]
                    args = args[1:]
                    timeshifted_entrypoint_args += (llvalue,)
                else:
                    is_constant = args[0]
                    llvalue     = args[1]
                    args = args[2:]
                    TYPE = lltype.typeOf(llvalue)
                    kind = rgenop.kindToken(TYPE)
                    boxcls = rvalue.ll_redboxcls(TYPE)
                    if is_constant:
                        # ignore the inputargs_gv[i], which is still present
                        # to give the residual graph a uniform signature
                        gv_arg = rgenop.genconst(llvalue)
                    else:
                        gv_arg = inputargs_gv[i]
                    box = boxcls(kind, gv_arg)
                    i += 1
                    timeshifted_entrypoint_args += (box,)

            top_jitstate = fresh_jitstate(builder, exceptiondesc)
            top_jitstate = timeshifted_entrypoint(top_jitstate,
                                                  *timeshifted_entrypoint_args)
            if top_jitstate is not None:
                finish_jitstate(top_jitstate, exceptiondesc, sigtoken)

            builder.end()
            generated = gv_generated.revealconst(lltype.Ptr(FUNC))
            return generated

        ml_generate_code.args_s = ["XXX rgenop"] + generate_code_args_s
        ml_generate_code.s_result = annmodel.lltype_to_annotation(
            lltype.Ptr(FUNC))

##        def ml_extract_residual_args(*args):
##            result = ()
##            for color in argcolors:
##                if color == "green":
##                    args = args[1:]
##                else:
##                    is_constant = args[0]
##                    llvalue     = args[1]
##                    args = args[2:]
##                    result += (llvalue,)
##            return result

##        def ml_call_residual_graph(generated, *allargs):
##            residual_args = ml_extract_residual_args(*allargs)
##            return generated(*residual_args)

##        ml_call_residual_graph.args_s = (
##            [ml_generate_code.s_result, ...])
##        ml_call_residual_graph.s_result = annmodel.lltype_to_annotation(
##            RESTYPE)

        self.ml_generate_code = ml_generate_code
##        self.ml_call_residual_graph = ml_call_residual_graph
        self.rtyper = rtyper
        self.hrtyper = hrtyper
        self.annotate_interface_functions()
        #if conftest.option.view and self.small:
        #    from pypy.translator.tool.graphpage import FlowGraphPage
        #    FlowGraphPage(t, ha.translator.graphs).display()

        cache = self.__dict__.copy()
        self._cache[key] = cache, getargtypes(rtyper.annotator, values)
        self._cache_order.append(key)
        return values

    def annotate_interface_functions(self):
        annhelper = self.hrtyper.annhelper
        RGenOp = self.RGenOp
        ml_generate_code = self.ml_generate_code
##        ml_call_residual_graph = self.ml_call_residual_graph

        def ml_main(*args):
            rgenop = RGenOp()
            return ml_generate_code(rgenop, *args)

        ml_main.args_s = ml_generate_code.args_s[1:]
        ml_main.s_result = ml_generate_code.s_result

        self.maingraph = annhelper.getgraph(
            ml_main,
            ml_main.args_s,
            ml_main.s_result)
##        self.callresidualgraph = annhelper.getgraph(
##            ml_call_residual_graph,
##            ml_call_residual_graph.args_s,
##            ml_call_residual_graph.s_result)

        annhelper.finish()

    def timeshift(self, ll_function, values, opt_consts=[], *args, **kwds):
        values = self.timeshift_cached(ll_function, values, *args, **kwds)

        mainargs = []
        residualargs = []
        for i, (color, llvalue) in enumerate(zip(self.argcolors, values)):
            if color == "green":
                mainargs.append(llvalue)
            else:
                mainargs.append(i in opt_consts)
                mainargs.append(llvalue)
                residualargs.append(llvalue)

        # run the graph generator
        exc_data_ptr = self.hrtyper.exceptiondesc.exc_data_ptr
        llinterp = LLInterpreter(self.rtyper, exc_data_ptr=exc_data_ptr)
        ll_generated = llinterp.eval_graph(self.maingraph, mainargs)

        # now try to run the residual graph generated by the builder
        residual_graph = ll_generated._obj.graph
        self.ll_generated = ll_generated
        self.residual_graph = residual_graph
        if conftest.option.view:
            residual_graph.show()

        if 'check_raises' not in kwds:
            res = llinterp.eval_graph(residual_graph, residualargs)
        else:
            try:
                llinterp.eval_graph(residual_graph, residualargs)
            except LLException, e:
                exc = kwds['check_raises']
                assert llinterp.find_exception(e) is exc, (
                    "wrong exception type")
            else:
                raise AssertionError("DID NOT RAISE")
            return True

        if hasattr(ll_function, 'convert_result'):
            res = ll_function.convert_result(res)

        # get some benchmarks with genc
        if Benchmark.ENABLED:
            from pypy.translator.interactive import Translation
            import sys
            testname = sys._getframe(1).f_code.co_name
            def ll_main():
                bench = Benchmark(testname)
                while True:
                    ll_generated(*residualargs)
                    if bench.stop():
                        break
            t = Translation(ll_main)
            main = t.compile_c([])
            main()
        return res

    def timeshift_raises(self, ExcCls, ll_function, values, opt_consts=[],
                         *args, **kwds):
        kwds['check_raises'] = ExcCls
        return self.timeshift(ll_function, values, opt_consts, *args, **kwds)

    def check_insns(self, expected=None, **counts):
        self.insns = summary(self.residual_graph)
        if expected is not None:
            assert self.insns == expected
        for opname, count in counts.items():
            assert self.insns.get(opname, 0) == count

    def check_oops(self, expected=None, **counts):
        if not self.on_llgraph:
            return
        oops = {}
        for block in self.residual_graph.iterblocks():
            for op in block.operations:
                if op.opname == 'direct_call':
                    f = getattr(op.args[0].value._obj, "_callable", None)
                    if hasattr(f, 'oopspec'):
                        name, _ = f.oopspec.split('(', 1)
                        oops[name] = oops.get(name, 0) + 1
        if expected is not None:
            assert oops == expected
        for name, count in counts.items():
            assert oops.get(name, 0) == count

    def check_flexswitches(self, expected_count):
        count = 0
        for block in self.residual_graph.iterblocks():
            if (isinstance(block.exitswitch, Variable) and
                block.exitswitch.concretetype is lltype.Signed):
                count += 1
        assert count == expected_count


class TestTimeshift(TimeshiftingTests):

    def test_simple_fixed(self):
        py.test.skip("green return not working")
        def ll_function(x, y):
            return hint(x + y, concrete=True)
        res = self.timeshift(ll_function, [5, 7])
        assert res == 12
        self.check_insns({})

    def test_very_simple(self):
        def ll_function(x, y):
            return x + y
        res = self.timeshift(ll_function, [5, 7])
        assert res == 12
        self.check_insns({'int_add': 1})

    def test_convert_const_to_redbox(self):
        def ll_function(x, y):
            x = hint(x, concrete=True)
            tot = 0
            while x:    # conversion from green '0' to red 'tot'
                tot += y
                x -= 1
            return tot
        res = self.timeshift(ll_function, [7, 2])
        assert res == 14
        self.check_insns({'int_add': 7})

    def test_simple_opt_const_propagation2(self):
        def ll_function(x, y):
            return x + y
        res = self.timeshift(ll_function, [5, 7], [0, 1])
        assert res == 12
        self.check_insns({})

    def test_simple_opt_const_propagation1(self):
        def ll_function(x):
            return -x
        res = self.timeshift(ll_function, [5], [0])
        assert res == -5
        self.check_insns({})

    def test_loop_folding(self):
        def ll_function(x, y):
            tot = 0
            x = hint(x, concrete=True)    
            while x:
                tot += y
                x -= 1
            return tot
        res = self.timeshift(ll_function, [7, 2], [0, 1])
        assert res == 14
        self.check_insns({})

    def test_loop_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            return tot
        res = self.timeshift(ll_function, [7, 2], [])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 2)

        res = self.timeshift(ll_function, [7, 2], [0])
        assert res == 14
        self.check_insns(int_add = 2,
                         int_is_true = 1)

        res = self.timeshift(ll_function, [7, 2], [1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 2)

        res = self.timeshift(ll_function, [7, 2], [0, 1])
        assert res == 14
        self.check_insns(int_add = 1,
                         int_is_true = 1)

    def test_two_loops_merging(self):
        def ll_function(x, y):
            tot = 0
            while x:
                tot += y
                x -= 1
            while y:
                tot += y
                y -= 1
            return tot
        res = self.timeshift(ll_function, [7, 3], [])
        assert res == 27
        self.check_insns(int_add = 3,
                         int_is_true = 3)

    def test_convert_greenvar_to_redvar(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            return x - y
        res = self.timeshift(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_sub = 1)
        res = self.timeshift(ll_function, [70, 4], [0, 1])
        assert res == 66
        self.check_insns({})

    def test_green_across_split(self):
        def ll_function(x, y):
            hint(x, concrete=True)
            if y > 2:
                z = x - y
            else:
                z = x + y
            return z
        res = self.timeshift(ll_function, [70, 4], [0])
        assert res == 66
        self.check_insns(int_add = 1,
                         int_sub = 1)

    def test_merge_const_before_return(self):
        def ll_function(x):
            if x > 0:
                y = 17
            else:
                y = 22
            x -= 1
            y += 1
            return y+x
        res = self.timeshift(ll_function, [-70], [])
        assert res == 23-71
        self.check_insns({'int_gt': 1, 'int_add': 2, 'int_sub': 2})

    def test_merge_3_redconsts_before_return(self):
        def ll_function(x):
            if x > 2:
                y = hint(54, variable=True)
            elif x > 0:
                y = hint(17, variable=True)
            else:
                y = hint(22, variable=True)
            x -= 1
            y += 1
            return y+x
        res = self.timeshift(ll_function, [-70], [])
        assert res == ll_function(-70)
        res = self.timeshift(ll_function, [1], [])
        assert res == ll_function(1)
        res = self.timeshift(ll_function, [-70], [])
        assert res == ll_function(-70)

    def test_merge_const_at_return(self):
        py.test.skip("green return")
        def ll_function(x):
            if x > 0:
                return 17
            else:
                return 22
        res = self.timeshift(ll_function, [-70], [])
        assert res == 22
        self.check_insns({'int_gt': 1})

    def test_arith_plus_minus(self):
        def ll_plus_minus(encoded_insn, nb_insn, x, y):
            acc = x
            pc = 0
            while pc < nb_insn:
                op = (encoded_insn >> (pc*4)) & 0xF
                op = hint(op, concrete=True)
                if op == 0xA:
                    acc += y
                elif op == 0x5:
                    acc -= y
                pc += 1
            return acc
        assert ll_plus_minus(0xA5A, 3, 32, 10) == 42
        res = self.timeshift(ll_plus_minus, [0xA5A, 3, 32, 10], [0, 1])
        assert res == 42
        self.check_insns({'int_add': 2, 'int_sub': 1})

    def test_simple_struct(self):
        S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                          ('world', lltype.Signed),
                            hints={'immutable': True})

        def ll_function(s):
            return s.hello * s.world

        def struct_S(string):
            items = string.split(',')
            assert len(items) == 2
            s1 = lltype.malloc(S)
            s1.hello = int(items[0])
            s1.world = int(items[1])
            return s1
        ll_function.convert_arguments = [struct_S]

        res = self.timeshift(ll_function, ["6,7"], [])
        assert res == 42
        self.check_insns({'getfield': 2, 'int_mul': 1})
        res = self.timeshift(ll_function, ["8,9"], [0])
        assert res == 72
        self.check_insns({})

    def test_simple_array(self):
        A = lltype.GcArray(lltype.Signed, 
                            hints={'immutable': True})
        def ll_function(a):
            return a[0] * a[1]

        def int_array(string):
            items = [int(x) for x in string.split(',')]
            n = len(items)
            a1 = lltype.malloc(A, n)
            for i in range(n):
                a1[i] = items[i]
            return a1
        ll_function.convert_arguments = [int_array]

        res = self.timeshift(ll_function, ["6,7"], [])
        assert res == 42
        self.check_insns({'getarrayitem': 2, 'int_mul': 1})
        res = self.timeshift(ll_function, ["8,3"], [0])
        assert res == 24
        self.check_insns({})



    def test_simple_struct_malloc(self):
        py.test.skip("blue containers: to be reimplemented")
        S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                          ('world', lltype.Signed))               
        def ll_function(x):
            s = lltype.malloc(S)
            s.hello = x
            return s.hello + s.world

        res = self.timeshift(ll_function, [3], [])
        assert res == 3
        self.check_insns({'int_add': 1})

        res = self.timeshift(ll_function, [3], [0])
        assert res == 3
        self.check_insns({})

    def test_inlined_substructure(self):
        py.test.skip("blue containers: to be reimplemented")
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            t.s.n = k
            l = t.s.n
            return l
        res = self.timeshift(ll_function, [7], [])
        assert res == 7
        self.check_insns({})

        res = self.timeshift(ll_function, [7], [0])
        assert res == 7
        self.check_insns({})

    def test_degenerated_before_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.timeshift(ll_function, [0], [])
        assert res == 5 * 3
        res = self.timeshift(ll_function, [1], [])
        assert res == 4 * 4

    def test_degenerated_before_return_2(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                pass
            else:
                s = t.s
            s.n += 1
            return s.n * t.s.n
        res = self.timeshift(ll_function, [1], [])
        assert res == 5 * 3
        res = self.timeshift(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerated_at_return(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        class Result:
            def convert(self, s):
                self.s = s
                return str(s.n)
        glob_result = Result()

        def ll_function(flag):
            t = lltype.malloc(T)
            t.n = 3.25
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            return s
        ll_function.convert_result = glob_result.convert

        res = self.timeshift(ll_function, [0], [])
        assert res == "4"
        if self.__class__ is TestTimeshift:
            assert lltype.parentlink(glob_result.s._obj) == (None, None)
        res = self.timeshift(ll_function, [1], [])
        assert res == "3"
        if self.__class__ is TestTimeshift:
            parent, parentindex = lltype.parentlink(glob_result.s._obj)
            assert parentindex == 's'
            assert parent.n == 3.25

    def test_degenerated_via_substructure(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 7
            if flag:
                pass
            else:
                s = t.s
            t.s.n += 1
            return s.n * t.s.n
        res = self.timeshift(ll_function, [1], [])
        assert res == 7 * 4
        res = self.timeshift(ll_function, [0], [])
        assert res == 4 * 4

    def test_degenerate_with_voids(self):
        S = lltype.GcStruct('S', ('y', lltype.Void),
                                 ('x', lltype.Signed))
        def ll_function():
            s = lltype.malloc(S)
            s.x = 123
            return s
        ll_function.convert_result = lambda s: str(s.x)
        res = self.timeshift(ll_function, [], [], policy=P_NOVIRTUAL)
        assert res == "123"

    def test_plus_minus_all_inlined(self):
        def ll_plus_minus(s, x, y):
            acc = x
            n = len(s)
            pc = 0
            while pc < n:
                op = s[pc]
                op = hint(op, concrete=True)
                if op == '+':
                    acc += y
                elif op == '-':
                    acc -= y
                pc += 1
            return acc
        ll_plus_minus.convert_arguments = [LLSupport.to_rstr, int, int]
        res = self.timeshift(ll_plus_minus, ["+-+", 0, 2], [0], inline=100000)
        assert res == ll_plus_minus("+-+", 0, 2)
        self.check_insns({'int_add': 2, 'int_sub': 1})

    def test_red_virtual_container(self):
        # this checks that red boxes are able to be virtualized dynamically by
        # the compiler (the P_NOVIRTUAL policy prevents the hint-annotator from
        # marking variables in blue)
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        def ll_function(n):
            s = lltype.malloc(S)
            s.n = n
            return s.n
        res = self.timeshift(ll_function, [42], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({})


    def test_setarrayitem(self):
        A = lltype.GcArray(lltype.Signed)
        a = lltype.malloc(A, 2, immortal=True)
        def ll_function():
            a[0] = 1
            a[1] = 2
            return a[0]+a[1]
        
        res = self.timeshift(ll_function, [], [], policy=P_NOVIRTUAL)
        assert res == 3

    def test_red_array(self):
         A = lltype.GcArray(lltype.Signed)
         def ll_function(x, y, n):
             a = lltype.malloc(A, 2)
             a[0] = x
             a[1] = y
             return a[n]*len(a)

         res = self.timeshift(ll_function, [21, -21, 0], [],
                              policy=P_NOVIRTUAL)
         assert res == 42
         self.check_insns({'malloc_varsize': 1,
                           'setarrayitem': 2, 'getarrayitem': 1,
                           'getarraysize': 1, 'int_mul': 1})

         res = self.timeshift(ll_function, [21, -21, 1], [],
                              policy=P_NOVIRTUAL)
         assert res == -42
         self.check_insns({'malloc_varsize': 1,
                           'setarrayitem': 2, 'getarrayitem': 1,
                           'getarraysize': 1, 'int_mul': 1})

    def test_red_struct_array(self):
         S = lltype.Struct('s', ('x', lltype.Signed))
         A = lltype.GcArray(S)
         def ll_function(x, y, n):
             a = lltype.malloc(A, 2)
             a[0].x = x
             a[1].x = y
             return a[n].x*len(a)

         res = self.timeshift(ll_function, [21, -21, 0], [],
                              policy=P_NOVIRTUAL)
         assert res == 42
         self.check_insns({'malloc_varsize': 1,
                           'getarraysubstruct': 3,
                           'setfield': 2, 'getfield': 1,
                           'getarraysize': 1, 'int_mul': 1})

         res = self.timeshift(ll_function, [21, -21, 1], [],
                              policy=P_NOVIRTUAL)
         assert res == -42
         self.check_insns({'malloc_varsize': 1,
                           'getarraysubstruct': 3,
                           'setfield': 2, 'getfield': 1,
                           'getarraysize': 1, 'int_mul': 1})


    def test_red_varsized_struct(self):
         A = lltype.Array(lltype.Signed)
         S = lltype.GcStruct('S', ('foo', lltype.Signed), ('a', A))
         def ll_function(x, y, n):
             s = lltype.malloc(S, 3)
             s.foo = len(s.a)-1
             s.a[0] = x
             s.a[1] = y
             return s.a[n]*s.foo

         res = self.timeshift(ll_function, [21, -21, 0], [],
                              policy=P_NOVIRTUAL)
         assert res == 42
         self.check_insns(malloc_varsize=1)

         res = self.timeshift(ll_function, [21, -21, 1], [],
                              policy=P_NOVIRTUAL)
         assert res == -42
         self.check_insns(malloc_varsize=1)

    def test_array_of_voids(self):
        A = lltype.GcArray(lltype.Void)
        def ll_function(n):
            a = lltype.malloc(A, 3)
            a[1] = None
            b = a[n]
            res = a, b
            keepalive_until_here(b)      # to keep getarrayitem around
            return res
        ll_function.convert_result = lambda x: str(len(x.item0))

        res = self.timeshift(ll_function, [2], [], policy=P_NOVIRTUAL)
        assert res == "3"

    def test_red_propagate(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        def ll_function(n, k):
            s = lltype.malloc(S)
            s.n = n
            if k < 0:
                return -123
            return s.n * k
        res = self.timeshift(ll_function, [3, 8], [], policy=P_NOVIRTUAL)
        assert res == 24
        self.check_insns({'int_lt': 1, 'int_mul': 1})

    def test_red_subcontainer(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            s = t.s
            s.n = k
            if k < 0:
                return -123
            result = s.n * (k-1)
            keepalive_until_here(t)
            return result
        res = self.timeshift(ll_function, [7], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({'int_lt': 1, 'int_mul': 1, 'int_sub': 1})


    def test_red_subcontainer_cast(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
        def ll_function(k):
            t = lltype.malloc(T)
            s = lltype.cast_pointer(lltype.Ptr(S), t)
            s.n = k
            if k < 0:
                return -123
            result = s.n * (k-1)
            keepalive_until_here(t)
            return result
        res = self.timeshift(ll_function, [7], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({'int_lt': 1, 'int_mul': 1, 'int_sub': 1})


    def test_merge_structures(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', lltype.Ptr(S)), ('n', lltype.Signed))

        def ll_function(flag):
            if flag:
                s = lltype.malloc(S)
                s.n = 1
                t = lltype.malloc(T)
                t.s = s
                t.n = 2
            else:
                s = lltype.malloc(S)
                s.n = 5
                t = lltype.malloc(T)
                t.s = s
                t.n = 6
            return t.n + t.s.n
        res = self.timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
        assert res == 5 + 6
        self.check_insns({'int_is_true': 1, 'int_add': 1})
        res = self.timeshift(ll_function, [1], [], policy=P_NOVIRTUAL)
        assert res == 1 + 2
        self.check_insns({'int_is_true': 1, 'int_add': 1})

    def test_call_simple(self):
        def ll_add_one(x):
            return x + 1
        def ll_function(y):
            return ll_add_one(y)
        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 6
        self.check_insns({'int_add': 1})

    def test_call_2(self):
        def ll_add_one(x):
            return x + 1
        def ll_function(y):
            return ll_add_one(y) + y
        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 11
        self.check_insns({'int_add': 2})

    def test_call_3(self):
        def ll_add_one(x):
            return x + 1
        def ll_two(x):
            return ll_add_one(ll_add_one(x)) - x
        def ll_function(y):
            return ll_two(y) * y
        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 10
        self.check_insns({'int_add': 2, 'int_sub': 1, 'int_mul': 1})

    def test_call_4(self):
        def ll_two(x):
            if x > 0:
                return x + 5
            else:
                return x - 4
        def ll_function(y):
            return ll_two(y) * y

        res = self.timeshift(ll_function, [3], [], policy=P_NOVIRTUAL)
        assert res == 24
        self.check_insns({'int_gt': 1, 'int_add': 1,
                          'int_sub': 1, 'int_mul': 1})

        res = self.timeshift(ll_function, [-3], [], policy=P_NOVIRTUAL)
        assert res == 21
        self.check_insns({'int_gt': 1, 'int_add': 1,
                          'int_sub': 1, 'int_mul': 1})

    def test_void_call(self):
        def ll_do_nothing(x):
            pass
        def ll_function(y):
            ll_do_nothing(y)
            return y

        res = self.timeshift(ll_function, [3], [], policy=P_NOVIRTUAL)
        assert res == 3

    def test_green_call(self):
        def ll_add_one(x):
            return x+1
        def ll_function(y):
            z = ll_add_one(y)
            z = hint(z, concrete=True)
            return hint(z, variable=True)

        res = self.timeshift(ll_function, [3], [0], policy=P_NOVIRTUAL)
        assert res == 4
        self.check_insns({})

    def test_split_on_green_return(self):
        def ll_two(x):
            if x > 0:
                return 17
            else:
                return 22
        def ll_function(x):
            n = ll_two(x)
            return hint(n+1, variable=True)
        res = self.timeshift(ll_function, [-70], [])
        assert res == 23
        self.check_insns({'int_gt': 1})

    def test_green_with_side_effects(self):
        S = lltype.GcStruct('S', ('flag', lltype.Bool))
        s = lltype.malloc(S)
        s.flag = False
        def ll_set_flag(s):
            s.flag = True
        def ll_function():
            s.flag = False
            ll_set_flag(s)
            return s.flag
        res = self.timeshift(ll_function, [], [])
        assert res == True
        self.check_insns({'setfield': 2, 'getfield': 1})

    def test_recursive_call(self):
        def ll_pseudo_factorial(n, fudge):
            k = hint(n, concrete=True)
            if n <= 0:
                return 1
            return n * ll_pseudo_factorial(n - 1, fudge + n) - fudge
        res = self.timeshift(ll_pseudo_factorial, [4, 2], [0])
        expected = ll_pseudo_factorial(4, 2)
        assert res == expected
        
    def test_recursive_with_red_termination_condition(self):
        py.test.skip('Does not terminate')
        def ll_factorial(n):
            if n <= 0:
                return 1
            return n * ll_factorial(n - 1)

        res = self.timeshift(ll_factorial, [5], [])
        assert res == 120
        
    def test_simple_indirect_call(self):
        def g1(v):
            return v * 2

        def g2(v):
            return v + 2

        def f(flag, v):
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v)

        res = self.timeshift(f, [0, 40], [0])
        assert res == 42
        self.check_insns({'int_add': 1})

    def test_normalize_indirect_call(self):
        def g1(v):
            return -17

        def g2(v):
            return v + 2

        def f(flag, v):
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v)

        res = self.timeshift(f, [0, 40], [0])
        assert res == 42
        self.check_insns({'int_add': 1})

        res = self.timeshift(f, [1, 40], [0])
        assert res == -17
        self.check_insns({})

    def test_normalize_indirect_call_more(self):
        def g1(v):
            if v >= 0:
                return -17
            else:
                return -155

        def g2(v):
            return v + 2

        def f(flag, v):
            w = g1(v)
            if hint(flag, concrete=True):
                g = g1
            else:
                g = g2
            return g(v) + w

        res = self.timeshift(f, [0, 40], [0])
        assert res == 25
        self.check_insns({'int_add': 2, 'int_ge': 1})

        res = self.timeshift(f, [1, 40], [0])
        assert res == -34
        self.check_insns({'int_ge': 2, 'int_add': 1})

        res = self.timeshift(f, [0, -1000], [0])
        assert res == f(False, -1000)
        self.check_insns({'int_add': 2, 'int_ge': 1})

        res = self.timeshift(f, [1, -1000], [0])
        assert res == f(True, -1000)
        self.check_insns({'int_ge': 2, 'int_add': 1})

    def test_simple_meth(self):
        class Base(object):
            def m(self):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self):
                return 42
            pass  # for inspect.getsource() bugs

        def f(flag):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m()

        res = self.timeshift(f, [0], [0], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({})

        res = self.timeshift(f, [0], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(indirect_call=0)

    def test_simple_red_meth(self):
        class Base(object):
            def m(self, n):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, n):
                return 21*n
            pass  # for inspect.getsource() bugs

        def f(flag, x):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m(x)

        res = self.timeshift(f, [0, 2], [0], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({'int_mul': 1})

    def test_simple_red_meth_vars_around(self):
        class Base(object):
            def m(self, n):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self, n):
                return 21*n
            pass  # for inspect.getsource() bugs

        def f(flag, x, y, z):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return (o.m(x)+y)-z

        res = self.timeshift(f, [0, 2, 7, 5], [0], policy=P_NOVIRTUAL)
        assert res == 44
        self.check_insns({'int_mul': 1, 'int_add': 1, 'int_sub': 1})              

    def test_compile_time_const_tuple(self):
        d = {(4, 5): 42, (6, 7): 12}
        def f(a, b):
            d1 = hint(d, deepfreeze=True)
            return d1[a, b]

        res = self.timeshift(f, [4, 5], [0, 1], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({})

    def test_green_red_mismatch_in_call(self):
        #py.test.skip("WIP")
        def add(a,b, u):
            return a+b

        def f(x, y, u):
            r = add(x+1,y+1, u)
            z = x+y
            z = hint(z, concrete=True) + r   # this checks that 'r' is green
            return hint(z, variable=True)

        res = self.timeshift(f, [4, 5, 0], [], policy=P_NOVIRTUAL)
        assert res == 20

    def test_residual_red_call(self):
        def g(x):
            return x+1

        def f(x):
            return 2*g(x)

        res = self.timeshift(f, [20], [], policy=StopAtXPolicy(g))
        assert res == 42
        self.check_insns(int_add=0)

    def test_residual_red_call_with_exc(self):
        def h(x):
            if x > 0:
                return x+1
            else:
                raise ValueError

        def g(x):
            return 2*h(x)

        def f(x):
            try:
                return g(x)
            except ValueError:
                return 7

        stop_at_h = StopAtXPolicy(h)
        res = self.timeshift(f, [20], [], policy=stop_at_h)
        assert res == 42
        self.check_insns(int_add=0)

        res = self.timeshift(f, [-20], [], policy=stop_at_h)
        assert res == 7
        self.check_insns(int_add=0)

    def test_red_call_ignored_result(self):
        def g(n):
            return n * 7
        def f(n, m):
            g(n)   # ignore the result
            return m

        res = self.timeshift(f, [4, 212], [], policy=P_NOVIRTUAL)
        assert res == 212

    def test_green_char_at_merge(self):
        def f(c, x):
            c = chr(c)
            c = hint(c, concrete=True)
            if x:
                x = 3
            else:
                x = 1
            c = hint(c, variable=True)
            return len(c*x)

        res = self.timeshift(f, [ord('a'), 1], [], policy=P_NOVIRTUAL)
        assert res == 3

        res = self.timeshift(f, [ord('b'), 0], [], policy=P_NOVIRTUAL)
        assert res == 1

    def test_self_referential_structures(self):
        S = lltype.GcForwardReference()
        S.become(lltype.GcStruct('s',
                                 ('ps', lltype.Ptr(S))))

        def f(x):
            s = lltype.malloc(S)
            if x:
                s.ps = lltype.malloc(S)
            return s
        def count_depth(s):
            x = 0
            while s:
                x += 1
                s = s.ps
            return str(x)
        
        f.convert_result = count_depth

        res = self.timeshift(f, [3], [], policy=P_NOVIRTUAL)
        assert res == '2'

    def test_known_nonzero(self):
        S = lltype.GcStruct('s', ('x', lltype.Signed))
        global_s = lltype.malloc(S, immortal=True)
        global_s.x = 100

        def h():
            s = lltype.malloc(S)
            s.x = 50
            return s
        def g(s, y):
            if s:
                return s.x * 5
            else:
                return -12 + y
        def f(x, y):
            x = hint(x, concrete=True)
            if x == 1:
                return g(lltype.nullptr(S), y)
            elif x == 2:
                return g(global_s, y)
            elif x == 3:
                s = lltype.malloc(S)
                s.x = y
                return g(s, y)
            elif x == 4:
                s = h()
                return g(s, y)
            else:
                s = h()
                if s:
                    return g(s, y)
                else:
                    return 0

        P = StopAtXPolicy(h)

        res = self.timeshift(f, [1, 10], [0], policy=P)
        assert res == -2
        self.check_insns(int_mul=0, int_add=1)

        res = self.timeshift(f, [2, 10], [0], policy=P)
        assert res == 500
        self.check_insns(int_mul=1, int_add=0)

        res = self.timeshift(f, [3, 10], [0], policy=P)
        assert res == 50
        self.check_insns(int_mul=1, int_add=0)

        res = self.timeshift(f, [4, 10], [0], policy=P)
        assert res == 250
        self.check_insns(int_mul=1, int_add=1)

        res = self.timeshift(f, [5, 10], [0], policy=P)
        assert res == 250
        self.check_insns(int_mul=1, int_add=0)

    def test_debug_assert_ptr_nonzero(self):
        S = lltype.GcStruct('s', ('x', lltype.Signed))
        def h():
            s = lltype.malloc(S)
            s.x = 42
            return s
        def g(s):
            # assumes that s is not null here
            debug_assert(bool(s), "please don't give me a null")
            return 5
        def f(m):
            s = h()
            n = g(s)
            if not s:
                n *= m
            return n

        P = StopAtXPolicy(h)

        res = self.timeshift(f, [17], [], policy=P)
        assert res == 5
        self.check_insns(int_mul=0)

    def test_indirect_red_call(self):
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            h = l[n&1]
            return h(n) + x

        P = StopAtXPolicy()
        res = self.timeshift(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1, direct_call=1)

    def test_indirect_red_call_with_exc(self):
        def h1(n):
            if n < 0:
                raise ValueError
            return n*2
        def h2(n):
            if n < 0:
                raise ValueError
            return n*4
        l = [h1, h2]
        def g(n, x):
            h = l[n&1]
            return h(n) + x

        def f(n, x):
            try:
                return g(n, x)
            except ValueError:
                return -1111

        P = StopAtXPolicy()
        res = self.timeshift(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1)

        res = self.timeshift(f, [-7, 3], policy=P)
        assert res == -1111
        self.check_insns(indirect_call=1)

    def test_indirect_gray_call(self):
        def h1(w, n):
            w[0] =  n*2
        def h2(w, n):
            w[0] = n*4
        l = [h1, h2]
        def f(n, x):
            w = [0]
            h = l[n&1]
            h(w, n)
            return w[0] + x

        P = StopAtXPolicy()
        res = self.timeshift(f, [7, 3], policy=P)
        assert res == f(7,3)

    def test_indirect_residual_red_call(self):
        def h1(n):
            return n*2
        def h2(n):
            return n*4
        l = [h1, h2]
        def f(n, x):
            h = l[n&1]
            return h(n) + x

        P = StopAtXPolicy(h1, h2)
        res = self.timeshift(f, [7, 3], policy=P)
        assert res == f(7,3)
        self.check_insns(indirect_call=1)

    def test_constant_indirect_red_call(self):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            return h(x)

        P = StopAtXPolicy()
        res = self.timeshift(f, [7, 3], [0], policy=P)
        assert res == f(7,3)
        self.check_insns({'int_mul': 1})
        res = self.timeshift(f, [4, 113], [0], policy=P)
        assert res == f(4,113)
        self.check_insns({'int_sub': 1})

    def test_indirect_sometimes_residual_pure_red_call(self):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            hint(None, global_merge_point=True)
            hint(n, concrete=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            return h(x)

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.timeshift(f, [7, 3], [], policy=P)
        assert res == f(7,3)
        self.check_insns({'int_mul': 1})
        res = self.timeshift(f, [4, 113], [], policy=P)
        assert res == f(4,113)
        self.check_insns({'direct_call': 1})

    def test_indirect_sometimes_residual_pure_but_fixed_red_call(self):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        l = [h1, h2]
        def f(n, x):
            hint(None, global_merge_point=True)
            frozenl = hint(l, deepfreeze=True)
            h = frozenl[n&1]
            z = h(x)
            hint(z, concrete=True)
            return z

        P = StopAtXPolicy(h1)
        P.oopspec = True
        res = self.timeshift(f, [7, 3], [], policy=P)
        assert res == f(7,3)
        self.check_insns({})
        res = self.timeshift(f, [4, 113], [], policy=P)
        assert res == f(4,113)
        self.check_insns({})

    def test_red_int_add_ovf(self):
        def f(n, m):
            try:
                return ovfcheck(n + m)
            except OverflowError:
                return -42

        res = self.timeshift(f, [100, 20])
        assert res == 120
        self.check_insns(int_add_ovf=1)
        res = self.timeshift(f, [sys.maxint, 1])
        assert res == -42
        self.check_insns(int_add_ovf=1)

    def test_green_int_add_ovf(self):
        def f(n, m):
            try:
                res = ovfcheck(n + m)
            except OverflowError:
                res = -42
            hint(res, concrete=True)
            return res

        res = self.timeshift(f, [100, 20])
        assert res == 120
        self.check_insns({})
        res = self.timeshift(f, [sys.maxint, 1])
        assert res == -42
        self.check_insns({})

    def test_nonzeroness_assert_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.timeshift(f, [42], policy=P_NOVIRTUAL)
        assert res == -7

    def test_segfault_while_compiling(self):
        class X:
            pass
        class Y:
            pass

        def g(x, y):
            x = hint(x, deepfreeze=True)
            if y.flag:
                return x.value
            else:
                return -7

        def h(n):
            if n:
                x = X()
                x.value = n
                return x
            else:
                return None

        y = Y()

        def f(n):
            y.flag = True
            g(h(n), y)
            y.flag = False
            return g(h(0), y)

        res = self.timeshift(f, [42], policy=P_NOVIRTUAL)
        assert res == -7
