import py, os
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import s_list_of_strings
from pypy.rlib.unroll import unrolling_iterable
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.jit.timeshifter.test import test_portal
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.rpython.annlowlevel import PseudoHighLevelCallable

class I386PortalTestMixin(object):
    RGenOp = RI386GenOp

    def postprocess_timeshifting(self):
        annhelper = self.hrtyper.annhelper
        convert_result = getattr(self.main, 'convert_result', str)
        annotator = self.rtyper.annotator
        args_s = [annmodel.lltype_to_annotation(v.concretetype)
                  for v in self.maingraph.getargs()]
        retvar = self.maingraph.getreturnvar()
        s_result = annmodel.lltype_to_annotation(retvar.concretetype)
        main_fnptr = self.rtyper.type_system.getcallable(self.maingraph)
        main = PseudoHighLevelCallable(main_fnptr, args_s, s_result)
        
        if hasattr(self.main, 'convert_arguments'):
            decoders = self.main.convert_arguments
            assert len(decoders) == len(args_s)
        else:
            decoders = [int] * len(args_s)
        decoders = unrolling_iterable(decoders)
        def ll_main(argv):
            args = ()
            i = 1
            for decoder in decoders:
                args += (decoder(argv[i]),)
                i = i + 1
            try:
                res = main(*args)
            except Exception, e:
                os.write(1, 'EXCEPTION: %s\n' % (e,))
                return 0
            os.write(1, convert_result(res) + '\n')
            return 0

        annhelper.getgraph(ll_main, [s_list_of_strings],
                           annmodel.SomeInteger())
        annhelper.finish()
        t = self.rtyper.annotator.translator
        t.config.translation.gc = 'boehm'
        self.cbuilder = CStandaloneBuilder(t, ll_main, config=t.config)
        self.cbuilder.generate_source()
        self.cbuilder.compile()
        
    def timeshift_from_portal(self, main, portal, main_args,
                              inline=None, policy=None,
                              backendoptimize=False):
        self.main = main
        self._timeshift_from_portal(main, portal, main_args,
                                    inline=inline, policy=policy,
                                    backendoptimize=backendoptimize)
        cmdargs = ' '.join([str(arg) for arg in main_args])
        output = self.cbuilder.cmdexec(cmdargs)
        lines = output.split()
        lastline = lines[-1]
        assert not lastline.startswith('EXCEPTION:')
        if hasattr(main, 'convert_result'):
            return lastline
        else:
            return int(lastline)    # assume an int
        
    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."
    
class TestPortal(I386PortalTestMixin,
                 test_portal.TestPortal):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_portal.py
    pass
