import py, os, sys
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import s_list_of_strings
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.jit.timeshifter.test import test_timeshift
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.jit.conftest import Benchmark


class I386TimeshiftingTestMixin(object):
    RGenOp = RI386GenOp

    SEPLINE = 'running residual graph...\n'
    
    def annotate_interface_functions(self):
        annhelper = self.hrtyper.annhelper
        RGenOp = self.RGenOp
        SEPLINE = self.SEPLINE
        ml_generate_code = self.ml_generate_code
        argcolors = list(self.argcolors)
        if hasattr(self.ll_function, 'convert_arguments'):
            decoders = self.ll_function.convert_arguments
            assert len(decoders) == len(argcolors)
        else:
            decoders = [int] * len(argcolors)
        argcolors_decoders = zip(argcolors, decoders)
        argcolors_decoders = unrolling_iterable(argcolors_decoders)
        convert_result = getattr(self.ll_function, 'convert_result', str)

        def ll_main(argv):
            i = 1
            mainargs = ()
            residualargs = ()
            if len(argv) == 2 and argv[1] == '--help':
                os.write(1, 'usage: ' + argv[0])
                for color, decoder in argcolors_decoders:
                    os.write(1, ' ')
                    if color == 'green':
                        os.write(1, decoder.__name__)
                    else:
                        os.write(1, "-const|-var "+decoder.__name__)
                os.write(1, '\n')
                return 0
            
            for color, decoder in argcolors_decoders:
                try:
                    if color == 'green':
                        llvalue = decoder(argv[i])
                        mainargs += (llvalue,)
                        i = i + 1
                    else:
                        if argv[i] == '-const':
                            is_const = True
                        elif argv[i] == '-var':
                            is_const = False
                        else:
                            raise ValueError()
                        i += 1
                        llvalue = decoder(argv[i])
                        mainargs += (is_const, llvalue)
                        residualargs += (llvalue,)
                        i += 1 
                except (ValueError, IndexError):
                    j = 1
                    while j < len(argv):
                        arg = argv[j]
                        if j == i:
                            os.write(1, '--> ')
                        else:
                            os.write(1, '    ')
                        os.write(1, arg+'\n')
                        j += 1
                    if j == i:
                        os.write(1, '-->\n')
                    return 1
            rgenop = RGenOp()
            generated = ml_generate_code(rgenop, *mainargs)
            os.write(1, SEPLINE)
            bench = Benchmark()
            while 1:
                try:
                    res = generated(*residualargs)
                except Exception, e:
                    os.write(1, 'EXCEPTION: %s\n' % (e,))
                    return 0
                if bench.stop():
                    break
            os.write(1, convert_result(res) + '\n')
            rgenop.check_no_open_mc()
            keepalive_until_here(rgenop)    # to keep the code blocks alive
            return 0
            
        annhelper.getgraph(ll_main, [s_list_of_strings],
                           annmodel.SomeInteger())
        annhelper.finish()
        t = self.rtyper.annotator.translator
        t.config.translation.gc = 'boehm'
        cbuilder = CStandaloneBuilder(t, ll_main, config=t.config)
        cbuilder.generate_source()
        cbuilder.compile()
        self.main_cbuilder= cbuilder
        
    def timeshift(self, ll_function, values, opt_consts=[], *args, **kwds):
        self.ll_function = ll_function
        self.timeshift_cached(ll_function, values, *args, **kwds)

        mainargs = []
        for i, (color, strvalue) in enumerate(zip(self.argcolors, values)):
            if color == "green":
                mainargs.append(strvalue)
            else:
                if i in opt_consts:
                    mainargs.append('-const')
                else:
                    mainargs.append('-var')
                mainargs.append(strvalue)

        mainargs = ' '.join([str(arg) for arg in mainargs])

        output = self.main_cbuilder.cmdexec(mainargs)
        lines = output.splitlines()
        assert lines[0] == self.SEPLINE[:-1]
        if (lines[1].startswith('{') and
            lines[1].endswith('iterations/second}')):
            testname = sys._getframe(1).f_code.co_name
            os.write(2, '{%s: %s\n' % (testname, lines.pop(1)[1:]))
        assert len(lines) == 2
        lastline = lines[1]
        if 'check_raises' in kwds:
            exc_name = kwds['check_raises'].__name__
            assert lastline.startswith('EXCEPTION: ')    # else DID NOT RAISE
            assert exc_name in lastline
            return True
        if hasattr(ll_function, 'convert_result'):
            return lastline
        else:
            return int(lastline)    # assume an int

    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."

    def check_flexswitches(self, expected_count):
        "Cannot check instructions in the generated assembler."

class TestTimeshiftI386(I386TimeshiftingTestMixin,
                        test_timeshift.TestLLType):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass
