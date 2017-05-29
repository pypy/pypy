import commands, os, sys, time, math

from math import atan
NNN = 10000000


def run_bench(bench):
    global t_loop_offset, NNN

    t1 = time.time()
    bench(NNN)
    t2 = time.time()

    t_bench = (t2-t1)
    return bench.scale*t_bench-t_loop_offset

def print_bench(name, t_bench):
    global t_cppref
    print ':::: %s cost: %#6.3fs (%#4.1fx)' % (name, t_bench, float(t_bench)/t_cppref)

def python_loop_offset():
    for i in xrange(NNN):
        i
    return i

class CPythonBench1(object):
    scale = 1
    def __init__(self):
        import ROOT
        ROOT.gROOT.SetBatch(1)
        ROOT.SetSignalPolicy(ROOT.kSignalFast)
        import cppyy
        self.lib = cppyy.gbl.gSystem.Load("./example01Dict.so")

        self.cls   = cppyy.gbl.example01
        self.inst  = self.cls(0)

    def __call__(self, repeat):
        # TODO: check linearity of actual scaling
        instance = self.inst
        niter = repeat/self.scale
        self.cls.addDataToInt._threaded = True
        for i in xrange(niter):
            instance.addDataToInt(i)
        return i

class CPythonBench1_Swig(object):
    scale = 1
    def __init__(self):
        import example

        self.cls   = example.example01
        self.inst  = self.cls(0)

    def __call__(self, repeat):
        # TODO: check linearity of actual scaling
        instance = self.inst
        niter = repeat/self.scale
        for i in xrange(niter):
            instance.addDataToInt(i)
        return i


class PureBench1(object):
    scale = 1
    def __init__(self):
        class example01(object):
            def __init__(self, somedata):
                self.m_somedata = somedata
            def addDataToInt(self, a):
                return self.m_somedata + int(atan(a))

        self.cls   = example01
        self.inst  = self.cls(0)

    def __call__(self, repeat):
        # TODO: check linearity of actual scaling
        instance = self.inst
        niter = repeat/self.scale
        for i in xrange(niter):
            instance.addDataToInt(i)
        return i


class CppyyInterpBench1(object):
    title = "cppyy interp"
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_reflection_info("./example01Dict.so")

        self.cls  = cppyy._scope_byname("example01")
        self.inst = self.cls.get_overload(self.cls.type_name).call(None, 0)

    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("addDataToInt")
        instance = self.inst
        for i in xrange(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyInterpBench2(CppyyInterpBench1):
    title = "... overload"
    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("overloadedAddDataToInt")
        instance = self.inst
        for i in xrange(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyInterpBench3(CppyyInterpBench1):
    title = "... constref"
    def __call__(self, repeat):
        addDataToInt = self.cls.get_overload("addDataToIntConstRef")
        instance = self.inst
        for i in xrange(repeat):
            addDataToInt.call(instance, i)
        return i

class CppyyPythonBench1(object):
    title = "cppyy python"
    scale = 1
    def __init__(self):
        import cppyy
        self.lib = cppyy.load_reflection_info("./example01Dict.so")

        self.cls = cppyy.gbl.example01
        self.inst = self.cls(0)

    def __call__(self, repeat):
        instance = self.inst
        for i in xrange(repeat):
            instance.addDataToInt(i)
        return i

class CppyyPythonBench2(CppyyPythonBench1):
    title = "... objbyval"
    def __call__(self, repeat):
        import cppyy
        pl = cppyy.gbl.payload(3.14)

        instance = self.inst
        for i in xrange(repeat):
            instance.copyCyclePayload(pl)
        return i

class CppyyPythonBench3(CppyyPythonBench1):
    title = "... objbyptr"
    def __call__(self, repeat):
        import cppyy
        pl = cppyy.gbl.payload(3.14)

        instance = self.inst
        for i in xrange(repeat):
            instance.cyclePayload(pl)
        return i


if __name__ == '__main__':
    python_loop_offset();

    # time python loop offset
    t1 = time.time()
    python_loop_offset()
    t2 = time.time()
    t_loop_offset = t2-t1

    # special cases for CPython
    if '-swig' in sys.argv:
        # runs SWIG
        cpython_bench1 = CPythonBench1_Swig()
    elif '-pure' in sys.argv:
        # runs pure python
        cpython_bench1 = PureBench1()
    elif not 'cppyy' in sys.builtin_module_names:
        # runs ROOT/cppyy.py
        cpython_bench1 = CPythonBench1()
    try:
        print run_bench(cpython_bench1)
        sys.exit(0)
    except NameError:
        pass

    # get C++ reference point
    if not os.path.exists("bench1.exe") or\
            os.stat("bench1.exe").st_mtime < os.stat("bench1.cxx").st_mtime:
        print "rebuilding bench1.exe ... "
        # the following is debatable, as pypy-c uses direct function
        # pointers, whereas that is only true for virtual functions in
        # the case of C++ (by default, anyway, it need not)
        # yes, shared library use is what's going on ...
#        os.system( "g++ -O2 bench1.cxx example01.cxx -o bench1.exe" )
        os.system( "g++ -O2 bench1.cxx -L. -lexample01Dict -o bench1.exe" )
    stat, cppref = commands.getstatusoutput("./bench1.exe")
    t_cppref = float(cppref)

    # create object
    benches = [
        CppyyInterpBench1(), CppyyInterpBench2(), CppyyInterpBench3(),
        CppyyPythonBench1(), CppyyPythonBench2(), CppyyPythonBench3() ]

    # warm-up
    print "warming up ... "
    for bench in benches:
        bench(2000)

    # to allow some consistency checking
    print "C++ reference uses %.3fs" % t_cppref

    # test runs ...
    for bench in benches:
        print_bench(bench.title, run_bench(bench))

    stat, t_cpython1 = commands.getstatusoutput("/home/wlav/aditi/pypy/bin/v5/pypy-c bench1.py - -pure")
    if stat:
        print 'CPython pure bench1 failed:'
        os.write(sys.stdout.fileno(), t_cpython1)
        print
        exit(stat)
    print_bench("pypy-c pure ", float(t_cpython1))

    stat, t_cpython1 = commands.getstatusoutput("python bench1.py - -pure")
    if stat:
        print 'CPython pure bench1 failed:'
        os.write(sys.stdout.fileno(), t_cpython1)
        print
        exit(stat)
    print_bench("CPython pure", float(t_cpython1))

    stat, t_cpython1 = commands.getstatusoutput("python bench1.py - -b")
    if stat:
        print 'CPython bench1 failed:'
        os.write(sys.stdout.fileno(), t_cpython1)
        print
        exit(stat)
    print_bench("CPython     ", float(t_cpython1))

    #stat, t_cpython1 = commands.getstatusoutput("python bench1.py - -swig")
    #if stat:
    #    print 'SWIG bench1 failed:'
    #    os.write(sys.stdout.fileno(), t_cpython1)
    #    print
    #    exit(stat)
    #print_bench("SWIG        ", float(t_cpython1))
