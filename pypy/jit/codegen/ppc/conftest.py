import py
from pypy.jit.codegen import detect_cpu


class Directory(py.test.collect.Directory):

    def run(self):
        import py; py.test.skip("in-progress")
        try:
            processor = detect_cpu.autodetect()
        except detect_cpu.ProcessorAutodetectError, e:
            py.test.skip(str(e))
        else:
            if processor != 'ppc':
                py.test.skip('detected a %r CPU' % (processor,))

        return super(Directory, self).run()

Option = py.test.Config.Option

option = py.test.Config.addoptions("ppc options",
        Option('--trap', action="store_true", default=False,
               dest="trap",
               help=""),
        Option('--debug-print', action="store_true", default=False,
               dest="debug_print",
               help=""))
