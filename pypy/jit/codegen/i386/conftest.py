import py
from pypy.jit.codegen import detect_cpu


class Directory(py.test.collect.Directory):

    def run(self):
        try:
            processor = detect_cpu.autodetect()
        except detect_cpu.ProcessorAutodetectError, e:
            py.test.skip(str(e))
        else:
            if processor != 'i386':
                py.test.skip('detected a %r CPU' % (processor,))

        return super(Directory, self).run()

Option = py.test.Config.Option

option = py.test.Config.addoptions("ppc options",
        Option('--interp', action="store_true", default=False,
               dest="interp",
               help="run the very slow genc_interp_* tests"),
        )
