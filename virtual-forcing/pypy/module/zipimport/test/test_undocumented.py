import zipimport
import py

import os
import py_compile
import shutil
import time
import zipfile
from pypy.conftest import gettestobjspace

TESTFN = '@test'

created_paths = dict.fromkeys(['_top_level',
                     os.path.join('_pkg', '__init__'),
                     os.path.join('_pkg', 'submodule'),
                     os.path.join('_pkg', '_subpkg', '__init__'),
                     os.path.join('_pkg', '_subpkg', 'submodule')
                               ])

def temp_zipfile(created_paths, source=True, bytecode=True):
    """Create a temporary zip file for testing.

    Clears zipimport._zip_directory_cache.

    """
    import zipimport, os, shutil, zipfile, py_compile
    example_code = 'attr = None'
    TESTFN = '@test'
    zipimport._zip_directory_cache.clear()
    zip_path = TESTFN + '.zip'
    bytecode_suffix = 'c'# if __debug__ else 'o'
    zip_file = zipfile.ZipFile(zip_path, 'w')
    for path in created_paths:
        if os.sep in path:
            directory = os.path.split(path)[0]
            if not os.path.exists(directory):
                os.makedirs(directory)
        code_path = path + '.py'
        try:
            temp_file = open(code_path, 'w')
            temp_file.write(example_code)
        finally:
            temp_file.close()
        if source:
            zip_file.write(code_path)
        if bytecode:
            py_compile.compile(code_path, doraise=True)
            zip_file.write(code_path + bytecode_suffix)
    zip_file.close()
    return os.path.abspath(zip_path)

def cleanup_zipfile(created_paths):
    import os, shutil
    bytecode_suffix = 'c'# if __debug__ else 'o'
    zip_path = '@test.zip'
    for path in created_paths:
        if os.sep in path:
            directory = os.path.split(path)[0]
            if os.path.exists(directory):
                shutil.rmtree(directory)
        else:
            for suffix in ('.py', '.py' + bytecode_suffix):
                if os.path.exists(path + suffix):
                    os.unlink(path + suffix)
    os.unlink(zip_path)

class AppTestZipImport:
    def setup_class(cls):
        space = gettestobjspace(usemodules=['zipimport', 'rctime'])
        cls.space = space
        source = "():\n" + str(py.code.Source(temp_zipfile).indent()) + "\n    return temp_zipfile"
        cls.w_temp_zipfile = space.appexec([], source)
        source = "():\n" + str(py.code.Source(cleanup_zipfile).indent())+ "\n    return cleanup_zipfile"
        cls.w_cleanup_zipfile = space.appexec([], source)
        cls.w_created_paths = space.wrap(created_paths)

    def test_inheritance(self):
        # Should inherit from ImportError.
        import zipimport
        assert issubclass(zipimport.ZipImportError, ImportError)

    def test_nonzip(self):
        import os
        import zipimport
        # ZipImportError should be raised if a non-zip file is specified.
        TESTFN = '@test'
        test_file = open(TESTFN, 'w')
        try:
            test_file.write("# Test file for zipimport.")
            raises(zipimport.ZipImportError,
                   zipimport.zipimporter, TESTFN)
        finally:
            test_file.close()
            os.unlink(TESTFN)

    def test_root(self):
        import zipimport, os
        raises(zipimport.ZipImportError, zipimport.zipimporter,
                            os.sep)


    def test_direct_path(self):
        # A zipfile should return an instance of zipimporter.
        import zipimport
        zip_path = self.temp_zipfile(self.created_paths)
        try:
            zip_importer = zipimport.zipimporter(zip_path)
            assert isinstance(zip_importer, zipimport.zipimporter)
            assert zip_importer.archive == zip_path
            assert zip_importer.prefix == ''
            assert zip_path in zipimport._zip_directory_cache
        finally:
            self.cleanup_zipfile(self.created_paths)

    def test_pkg_path(self):
        # Thanks to __path__, need to be able to work off of a path with a zip
        # file at the front and a path for the rest.
        import zipimport, os
        zip_path = self.temp_zipfile(self.created_paths)
        try:
            prefix = '_pkg'
            path = os.path.join(zip_path, prefix)
            zip_importer = zipimport.zipimporter(path)
            assert isinstance(zip_importer, zipimport.zipimporter)
            assert zip_importer.archive == zip_path
            assert zip_importer.prefix == prefix
            assert zip_path in zipimport._zip_directory_cache
        finally:
            self.cleanup_zipfile(self.created_paths)

    def test_zip_directory_cache(self):
        # Test that _zip_directory_cache is set properly.
        # Using a package entry to test using a hard example.
        import zipimport, os
        zip_path = self.temp_zipfile(self.created_paths, bytecode=False)
        try:
            importer = zipimport.zipimporter(os.path.join(zip_path, '_pkg'))
            assert zip_path in zipimport._zip_directory_cache
            file_set = set(zipimport._zip_directory_cache[zip_path].iterkeys())
            compare_set = set(path.replace(os.path.sep, '/') + '.py'
                              for path in self.created_paths)
            assert file_set == compare_set
        finally:
            self.cleanup_zipfile(self.created_paths)
