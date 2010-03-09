
""" Base class for all posixish platforms
"""

from pypy.translator.platform import Platform, log, _run_subprocess
from pypy.tool import autopath
import py, os

class BasePosix(Platform):
    exe_ext = ''
    make_cmd = 'make'

    relevant_environ=['CPATH', 'LIBRARY_PATH', 'C_INCLUDE_PATH']

    def __init__(self, cc=None):
        if cc is None:
            cc = 'gcc'
        self.cc = cc

    def _libs(self, libraries):
        return ['-l%s' % (lib,) for lib in libraries]

    def _libdirs(self, library_dirs):
        return ['-L%s' % (ldir,) for ldir in library_dirs]

    def _includedirs(self, include_dirs):
        return ['-I%s' % (idir,) for idir in include_dirs]

    def _linkfiles(self, link_files):
        return list(link_files)

    def _compile_c_file(self, cc, cfile, compile_args):
        oname = cfile.new(ext='o')
        args = ['-c'] + compile_args + [str(cfile), '-o', str(oname)]
        self._execute_c_compiler(cc, args, oname)
        return oname

    def _link(self, cc, ofiles, link_args, standalone, exe_name):
        args = [str(ofile) for ofile in ofiles] + link_args
        args += ['-o', str(exe_name)]
        if not standalone:
            args = self._args_for_shared(args)
        self._execute_c_compiler(cc, args, exe_name)
        return exe_name

    def _preprocess_dirs(self, include_dirs):
        # hook for maemo
        return include_dirs

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]

        if path is None:
            path = cfiles[0].dirpath()

        pypypath = py.path.local(autopath.pypydir)

        if exe_name is None:
            exe_name = cfiles[0].new(ext=self.exe_ext)

        m = GnuMakefile(path)
        m.exe_name = exe_name
        m.eci = eci

        def pypyrel(fpath):
            rel = py.path.local(fpath).relto(pypypath)
            if rel:
                return os.path.join('$(PYPYDIR)', rel)
            else:
                return fpath

        rel_cfiles = [m.pathrel(cfile) for cfile in cfiles]
        rel_ofiles = [rel_cfile[:-2]+'.o' for rel_cfile in rel_cfiles]
        m.cfiles = rel_cfiles

        rel_includedirs = [pypyrel(incldir) for incldir in
                           self._preprocess_dirs(eci.include_dirs)]

        m.comment('automatically generated makefile')
        definitions = [
            ('PYPYDIR', autopath.pypydir),
            ('TARGET', exe_name.basename),
            ('DEFAULT_TARGET', '$(TARGET)'),
            ('SOURCES', rel_cfiles),
            ('OBJECTS', rel_ofiles),
            ('LIBS', self._libs(eci.libraries)),
            ('LIBDIRS', self._libdirs(eci.library_dirs)),
            ('INCLUDEDIRS', self._includedirs(rel_includedirs)),
            ('CFLAGS', self.cflags + list(eci.compile_extra)),
            ('LDFLAGS', self.link_flags + list(eci.link_extra)),
            ('CC', self.cc),
            ('CC_LINK', eci.use_cpp_linker and 'g++' or '$(CC)'),
            ('LINKFILES', eci.link_files),
            ]
        for args in definitions:
            m.definition(*args)

        rules = [
            ('all', '$(DEFAULT_TARGET)', []),
            ('$(TARGET)', '$(OBJECTS)', '$(CC_LINK) $(LDFLAGS) -o $@ $(OBJECTS) $(LIBDIRS) $(LIBS) $(LINKFILES)'),
            ('%.o', '%.c', '$(CC) $(CFLAGS) -o $@ -c $< $(INCLUDEDIRS)'),
            ]

        for rule in rules:
            m.rule(*rule)

        return m

    def execute_makefile(self, path_to_makefile):
        if isinstance(path_to_makefile, GnuMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('make in %s' % (path,))
        returncode, stdout, stderr = _run_subprocess(self.make_cmd, ['-C', str(path)])
        self._handle_error(returncode, stdout, stderr, path.join('make'))

class Definition(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def write(self, f):
        def write_list(prefix, lst):
            for i, fn in enumerate(lst):
                fn = fn.replace('\\', '\\\\')
                print >> f, prefix, fn,
                if i < len(lst)-1:
                    print >> f, '\\'
                else:
                    print >> f
                prefix = ' ' * len(prefix)
        name, value = self.name, self.value
        if isinstance(value, str):
            f.write('%s = %s\n' % (name, value.replace('\\', '\\\\')))
        else:
            write_list('%s =' % (name,), value)
        if value:
            f.write('\n')
        
class Rule(object):
    def __init__(self, target, deps, body):
        self.target = target
        self.deps   = deps
        self.body   = body

    def write(self, f):
        target, deps, body = self.target, self.deps, self.body
        if isinstance(deps, str):
            dep_s = deps
        else:
            dep_s = ' '.join(deps)
        f.write('%s: %s\n' % (target, dep_s))
        if isinstance(body, str):
            f.write('\t%s\n' % body)
        elif body:
            f.write('\t%s\n' % '\n\t'.join(body))
        f.write('\n')

class Comment(object):
    def __init__(self, body):
        self.body = body

    def write(self, f):
        f.write('# %s\n' % (self.body,))

class GnuMakefile(object):
    def __init__(self, path=None):
        self.defs = {}
        self.lines = []
        self.makefile_dir = py.path.local(path)
        
    def pathrel(self, fpath):
        if fpath.dirpath() == self.makefile_dir:
            return fpath.basename
        elif fpath.dirpath().dirpath() == self.makefile_dir.dirpath():
            path = '../' + fpath.relto(self.makefile_dir.dirpath())
            return path.replace('\\', '/')
        else:
            return str(fpath)

    def definition(self, name, value):
        defs = self.defs
        defn = Definition(name, value)
        if name in defs:
            self.lines[defs[name]] = defn
        else:
            defs[name] = len(self.lines)
            self.lines.append(defn)

    def rule(self, target, deps, body):
        self.lines.append(Rule(target, deps, body))

    def comment(self, body):
        self.lines.append(Comment(body))

    def write(self, out=None):
        if out is None:
            f = self.makefile_dir.join('Makefile').open('w')
        else:
            f = out
        for line in self.lines:
            line.write(f)
        f.flush()
        if out is None:
            f.close()
