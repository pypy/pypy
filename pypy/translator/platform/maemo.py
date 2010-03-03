import py, os
from pypy.translator.platform.linux import Linux, _run_subprocess, GnuMakefile
from pypy.translator.platform import ExecutionResult, log
from pypy.tool.udir import udir
from pypy.tool import autopath

def check_scratchbox():
    # in order to work, that file must exist and be executable by us
    if not os.access('/scratchbox/login', os.X_OK):
        py.test.skip("No scratchbox detected")

class Maemo(Linux):
    name = "maemo"
    
    available_includedirs = ['/usr/include', '/tmp']
    copied_cache = {}

    def _invent_new_name(self, basepath, base):
        pth = basepath.join(base)
        num = 0
        while pth.check():
            pth = basepath.join('%s_%d' % (base,num))
            num += 1
        return pth.ensure(dir=1)

    def _copy_files_to_new_dir(self, dir_from, pattern='*.[ch]'):
        try:
            return self.copied_cache[dir_from]
        except KeyError:
            new_dirpath = self._invent_new_name(udir, 'copied_includes')
            files = py.path.local(dir_from).listdir(pattern)
            for f in files:
                f.copy(new_dirpath)
            # XXX <hack for pypy>
            srcdir = py.path.local(dir_from).join('src')
            if srcdir.check(dir=1):
                target = new_dirpath.join('src').ensure(dir=1)
                for f in srcdir.listdir(pattern):
                    f.copy(target)
            # XXX </hack for pypy>
            self.copied_cache[dir_from] = new_dirpath
            return new_dirpath
    
    def _preprocess_dirs(self, include_dirs):
        """ Tweak includedirs so they'll be available through scratchbox
        """
        res_incl_dirs = []
        for incl_dir in include_dirs:
            incl_dir = py.path.local(incl_dir)
            for available in self.available_includedirs:
                if incl_dir.relto(available):
                    res_incl_dirs.append(str(incl_dir))
                    break
            else:
                # we need to copy files to a place where it's accessible
                res_incl_dirs.append(self._copy_files_to_new_dir(incl_dir))
        return res_incl_dirs
    
    def _execute_c_compiler(self, cc, args, outname):
        log.execute('/scratchbox/login ' + cc + ' ' + ' '.join(args))
        args = [cc] + args
        returncode, stdout, stderr = _run_subprocess('/scratchbox/login', args)
        self._handle_error(returncode, stderr, stdout, outname)
    
    def execute(self, executable, args=[], env=None):
        if isinstance(args, str):
            args = str(executable) + ' ' + args
            log.message('executing /scratchbox/login ' + args)
        else:
            args = [str(executable)] + args
            log.message('executing /scratchbox/login ' + ' '.join(args))
        returncode, stdout, stderr = _run_subprocess('/scratchbox/login', args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

    def include_dirs_for_libffi(self):
        # insanely obscure dir
        return ['/usr/include/arm-linux-gnueabi/']

    def library_dirs_for_libffi(self):
        # on the other hand, library lands in usual place...
        return []

    def execute_makefile(self, path_to_makefile):
        if isinstance(path_to_makefile, GnuMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('make in %s' % (path,))
        returncode, stdout, stderr = _run_subprocess('/scratchbox/login', ['make', '-C', str(path)])
        self._handle_error(returncode, stdout, stderr, path.join('make'))
