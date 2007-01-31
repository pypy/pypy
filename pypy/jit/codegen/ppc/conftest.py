import py
from pypy.jit.codegen import detect_cpu


class Directory(py.test.collect.Directory):

    def run(self):
        try:
            processor = detect_cpu.autodetect()
        except detect_cpu.ProcessorAutodetectError, e:
            py.test.skip(str(e))
        else:
            if processor != 'ppc':
                py.test.skip('detected a %r CPU' % (processor,))

        return super(Directory, self).run()

Option = py.test.config.Option

option = py.test.config.addoptions("ppc options",
        Option('--run-interp-tests', action="store_true", default=False,
               dest="run_interp_tests",
               help=""),
        Option('--debug-scribble', action="store_true", default=False,
               dest="debug_scribble",
               help="write junk into unused registers and regions of the stack"),
        Option('--debug-print', action="store_true", default=False,
               dest="debug_print",
               help=""))
