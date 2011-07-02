import py, os
from pypy.translator.platform.linux import Linux
from pypy.translator.platform.posix import _run_subprocess, GnuMakefile
from pypy.translator.platform import ExecutionResult, log
from pypy.tool.udir import udir
from pypy.tool import autopath
from os import getenv

SB2 = getenv('SB2')
if SB2 is None:
    log.error('SB2: Provide a path to the sb2 rootfs for the target in env variable SB2')
    assert 0

sb2_params = getenv('SB2OPT')
if sb2_params is None:
    log.info('Pass additional options to sb2 in SB2OPT')
    SB2ARGS = []
else:
    SB2ARGS = sb2_params.split(' ')

class ARM(Linux):
    name = "arm"

    available_includedirs = (SB2 + '/usr/include', '/tmp')
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

    def _preprocess_include_dirs(self, include_dirs):
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

    def _execute_c_compiler(self, cc, args, outname, cwd=None):
        log.execute('sb2 ' + ' '.join(SB2ARGS) + ' ' + cc + ' ' + ' '.join(args))
        args = SB2ARGS + [cc] + args
        returncode, stdout, stderr = _run_subprocess('sb2', args)
        self._handle_error(returncode, stderr, stdout, outname)

    def execute(self, executable, args=[], env=None):
        if isinstance(args, str):
            args = ' '.join(SB2ARGS) + ' ' + str(executable) + ' ' + args
            log.message('executing sb2 ' + args)
        else:
            args = SB2ARGS + [str(executable)] + args
            log.message('executing sb2 ' + ' '.join(args))
        returncode, stdout, stderr = _run_subprocess('sb2', args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

    def include_dirs_for_libffi(self):
        return [SB2 + '/usr/include/arm-linux-gnueabi/']

    def library_dirs_for_libffi(self):
        # on the other hand, library lands in usual place...
        return []

    def execute_makefile(self, path_to_makefile, extra_opts=[]):
        if isinstance(path_to_makefile, GnuMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('sb2 %s make %s in %s' % (' '.join(SB2ARGS), " ".join(extra_opts), path))
        returncode, stdout, stderr = _run_subprocess(
            'sb2', SB2ARGS + ['make', '-C', str(path)] + extra_opts)
        self._handle_error(returncode, stdout, stderr, path.join('make'))
