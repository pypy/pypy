#!/usr/bin/env python

import sys
import autopath
from time import clock
from py.compat import subprocess
from pypy.translator.interactive import Translation

LOOPS = 10000000

class MetaBench(type):
    def __new__(self, cls_name, bases, cls_dict):
        loop = cls_dict['loop']
        loop._dont_inline_ = True
        myglob = {
            'init': cls_dict['init'],
            'loop': loop,
            'LOOPS': cls_dict.get('LOOPS', LOOPS),
            'clock': clock,
            }
        args = ', '.join(cls_dict['args'])
        source = """
def %(cls_name)s():
    obj = init()
    start = clock()
    for i in xrange(LOOPS):
        loop(%(args)s)
    return clock() - start
""" % locals()
        exec source in myglob
        func = myglob[cls_name]
        func.benchmark = True
        return func


def run_benchmark(exe):
    from pypy.translator.cli.test.runtest import CliFunctionWrapper
    from pypy.translator.jvm.test.runtest import JvmGeneratedSourceWrapper
    
    if exe.__class__ in [CliFunctionWrapper,JvmGeneratedSourceWrapper]:
        stdout, stderr, retval = exe.run()
    else:
        assert isinstance(exe, str)
        bench = subprocess.Popen(exe, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = bench.communicate()
        retval = bench.wait()
    
    if retval != 0:
        print 'Running benchmark failed'
        print 'Standard Output:'
        print stdout
        print '-' * 40
        print 'Standard Error:'
        print stderr
        raise SystemExit(-1)
    
    mydict = {}
    for line in stdout.splitlines():
        name, res = line.split(':')
        mydict[name.strip()] = float(res)
    return mydict

def import_benchmarks():
    modules = sys.argv[1:]
    if len(modules) == 0:
        # import all the microbenchs
        from glob import glob
        for module in glob('*.py'):
            if module not in ('__init__.py', 'autopath.py', 'microbench.py'):
                modules.append(module)
    
    for module in modules:
        module = module.rstrip('.py')
        exec 'from %s import *' % module in globals()

def main():
    import_benchmarks()
    benchmarks = []
    for name, thing in globals().iteritems():
        if getattr(thing, 'benchmark', False):
            benchmarks.append((name, thing))
    benchmarks.sort()
    
    def entry_point(argv):
        for name, func in benchmarks:
            print name, ':', func()
        return 0
    
    t = Translation(entry_point, standalone=True, backend='c')
    c_exe = t.compile()
    t = Translation(entry_point, standalone=True, backend='cli')
    cli_exe = t.compile()
    t = Translation(entry_point, standalone=True, backend='jvm')
    jvm_exe = t.compile()
  
    c_res = run_benchmark(c_exe)
    cli_res = run_benchmark(cli_exe)
    jvm_res = run_benchmark(jvm_exe)
    
    print 'benchmark                              genc     gencli     cli_ratio   genjvm     jvm_ratio'
    print
    for name, _ in benchmarks:
        c_time = c_res[name]
        cli_time = cli_res[name]
        jvm_time = jvm_res[name]
        if c_time == 0:
            cli_ratio = '%10s' % '---'
        else:
            cli_ratio = '%10.2f' % (cli_time/c_time)
        if c_time == 0:
            jvm_ratio = '%10s' % '---'
        else:
            jvm_ratio = '%10.2f' % (jvm_time/c_time)
        print '%-32s %10.2f %10.2f %s %10.2f %s' % (name, c_time, cli_time, cli_ratio, jvm_time, jvm_ratio)

if __name__ == '__main__':
    main()
