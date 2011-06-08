import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestImport(BaseTestPyPyC):

    def test_import_in_function(self):
        def main(n):
            i = 0
            while i < n:
                from sys import version  # ID: import
                i += 1
            return i
        #
        log = self.run(main, [500])
        assert log.result == 500
        loop, = log.loops_by_id('import')
        assert loop.match_by_id('import', """
            p11 = getfield_gc(ConstPtr(ptr10), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            guard_value(p11, ConstPtr(ptr12), descr=<Guard4>)
            guard_not_invalidated(descr=<Guard5>)
            p14 = getfield_gc(ConstPtr(ptr13), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            p16 = getfield_gc(ConstPtr(ptr15), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            guard_value(p14, ConstPtr(ptr17), descr=<Guard6>)
            guard_isnull(p16, descr=<Guard7>)
        """)

    def test_import_fast_path(self, tmpdir):
        pkg = tmpdir.join('mypkg').ensure(dir=True)
        pkg.join('__init__.py').write("")
        pkg.join('mod.py').write(str(py.code.Source("""
            def do_the_import():
                import sys
        """)))
        def main(path, n):
            import sys
            sys.path.append(path)
            from mypkg.mod import do_the_import
            for i in range(n):
                do_the_import()
        #
        log = self.run(main, [str(tmpdir), 300])
        loop, = log.loops_by_filename(self.filepath)
        # this is a check for a slow-down that introduced a
        # call_may_force(absolute_import_with_lock).
        for opname in log.opnames(loop.allops(opcode="IMPORT_NAME")):
            assert 'call' not in opname    # no call-like opcode
