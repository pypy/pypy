using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using pypy.runtime;

namespace pypy.builtin
{
    interface IFile
    {
        FileStream GetStream();
        void Write(string buffer);
        string Read(int count);
    }

    // this class is used only for stdin/stdout/stderr
    class TextFile: IFile
    {
        private FileStream stream;
        private TextWriter writer;
        private TextReader reader;
        public TextFile(FileStream stream, TextReader reader, TextWriter writer)
        {
            this.stream = stream;
            this.writer = writer;
            this.reader = reader;
        }
        
        public FileStream GetStream()
        {
            return stream;
        }

        public void Write(string buffer)
        {
            if (writer == null)
                Helpers.raise_OSError(Errno.EBADF);
            writer.Write(buffer);
        }
        
        public string Read(int count)
        {
            if (reader == null)
                Helpers.raise_OSError(Errno.EBADF);
            char[] buf = new char[count];
            int n = reader.Read(buf, 0, count);
            return new string(buf, 0, n);
        }
    }

    abstract class AbstractFile: IFile
    {
        protected FileStream stream;

        protected abstract string _Read(int count);
        protected abstract void _Write(string buffer);

        public AbstractFile(FileStream stream)
        {
            this.stream = stream;
        }

        public FileStream GetStream()
        {
            return stream;
        }

        public void Write(string buffer)
        {
            if (!stream.CanWrite)
                Helpers.raise_OSError(Errno.EBADF);
            _Write(buffer);
        }

        public string Read(int count)
        {
            if (!stream.CanRead)
                Helpers.raise_OSError(Errno.EBADF);
            return _Read(count);
        }
    }

    class CRLFTextFile: AbstractFile
    {
        public CRLFTextFile(FileStream stream): base(stream)
        {
        }
        
        protected override void _Write(string buffer)
        {
            foreach(char ch in buffer) {
                if (ch == '\n')
                    stream.WriteByte((byte)'\r');
                stream.WriteByte((byte)ch);
            }
        }

        protected override string _Read(int count)
        {
            System.Text.StringBuilder builder = new System.Text.StringBuilder(count);
            bool pending_CR = false;
            while (count-- > 0) {
                int ch = stream.ReadByte();
                if (ch == -1)
                    break;
                else if (ch == '\r')
                    pending_CR = true;
                else {
                    if (pending_CR && ch != '\n')
                        builder.Append('\r');
                    builder.Append((char)ch);
                    pending_CR = false;
                }
            }
            return builder.ToString();
        }
    }

    class BinaryFile: AbstractFile
    {
        public BinaryFile(FileStream stream): base(stream)
        {
        }
        
        protected override void _Write(string buffer)
        {
            foreach(char ch in buffer)
                stream.WriteByte((byte)ch);
        }

        protected override string _Read(int count)
        {
             byte[] rawbuf = new byte[count];
             int n = stream.Read(rawbuf, 0, count);
             char[] buf = new char[count];
             for(int i=0; i<count; i++)
                 buf[i] = (char)rawbuf[i];
             return new string(buf, 0, n);
        }
    }

    public class ll_os
    {
        private static Dictionary<int, IFile> FileDescriptors;
        private static int fdcount;
        private static Dictionary<int, string> ErrorMessages;
        
        // NB: these values are those used by Windows and they differs
        // from the Unix ones; the os module is patched with these
        // values before flowgraphing to make sure we get the very
        // same values on each platform we do the compilation.
        private const int O_RDONLY = 0x0000;
        private const int O_WRONLY = 0x0001;
        private const int O_RDWR   = 0x0002;
        private const int O_APPEND = 0x0008;
        private const int O_CREAT  = 0x0100;
        private const int O_TRUNC  = 0x0200;
        private const int O_TEXT   = 0x4000;
        private const int O_BINARY = 0x8000;

        private const int S_IFMT = 61440;
        private const int S_IFDIR = 16384;
        private const int S_IFREG = 32768;

        static ll_os()
        {
            ErrorMessages = new Dictionary<int, string>();
            FileDescriptors = new Dictionary<int, IFile>();
            // XXX: what about CRLF conversion for stdin, stdout and stderr?
            // It seems that Posix let you read from stdout and
            // stderr, so pass Console.In to them, too.
            FileDescriptors[0] = new TextFile(null, Console.In, null);
            FileDescriptors[1] = new TextFile(null, Console.In, Console.Out);
            FileDescriptors[2] = new TextFile(null, Console.In, Console.Error);
            fdcount = 2; // 0, 1 and 2 are already used by stdin, stdout and stderr
        }

        private static void raise_OSError(int errno, string msg)
        {
            ErrorMessages[errno] = msg;
            Helpers.raise_OSError(errno);
        }

        public static string ll_os_strerror(int errno)
        {
            try {
                string msg = ErrorMessages[errno];
                ErrorMessages.Remove(errno);
                return msg;
            }
            catch(KeyNotFoundException e) {
                return "error " + errno;
            }
        }

        public static string ll_os_getcwd()
        {
            return System.IO.Directory.GetCurrentDirectory();
        }

        private static IFile getfd(int fd)
        {
            IFile f = FileDescriptors[fd];
            if (f == null)
                raise_OSError(Errno.EBADF, string.Format("Invalid file descriptor: {0}", fd));

            return f;
        }

        private static FileAccess get_file_access(int flags)
        {
            if ((flags & O_RDWR) != 0) return FileAccess.ReadWrite;
            if ((flags & O_WRONLY) != 0) return FileAccess.Write;
            return FileAccess.Read;
        }

        private static FileMode get_file_mode(int flags) {
            if ((flags & O_APPEND) !=0 ) return FileMode.Append;
            if ((flags & O_TRUNC) !=0 ) return FileMode.Create;
            if ((flags & O_CREAT) !=0 ) return FileMode.OpenOrCreate;
            return FileMode.Open;
        }

        public static int ll_os_open(string name, int flags, int mode)
        {
            FileAccess f_access = get_file_access(flags);
            FileMode f_mode = get_file_mode(flags);
            FileStream stream;
            IFile f;

            try {
                stream = new FileStream(name, f_mode, f_access, FileShare.ReadWrite);
            }
            catch(UnauthorizedAccessException e) {
                raise_OSError(Errno.EACCES, e.Message);
                return -1;
            }
            catch(FileNotFoundException e) {
                raise_OSError(Errno.ENOENT, e.Message);
                return -1;
            }
            catch(IOException e) {
                raise_OSError(Errno.EIO, e.Message);
                return -1;
            }

            // - on Unix there is no difference between text and binary modes
            // - on Windows text mode means that we should convert '\n' from and to '\r\n'
            // - on Mac < OS9 text mode means that we should convert '\n' from and to '\r' -- XXX: TODO!
            if ((flags & O_BINARY) == 0 && System.Environment.NewLine == "\r\n")
                f = new CRLFTextFile(stream);
            else
                f = new BinaryFile(stream);

            fdcount++;
            FileDescriptors[fdcount] = f;
            return fdcount;
        }

        public static void ll_os_close(int fd)
        {
            FileStream stream = getfd(fd).GetStream();
            if (stream != null)  // stdin/stdout/stderr files don't have a stream
                stream.Close();
            FileDescriptors.Remove(fd);
        }

        public static int ll_os_write(int fd, string buffer)
        {
            getfd(fd).Write(buffer);
            return buffer.Length;
        }

        /*
        private static void PrintString(string source, string s)
        {
            Console.Error.WriteLine(source);
            Console.Error.WriteLine(s);
            Console.Error.WriteLine("Length: {0}", s.Length);
            for (int i=0; i<s.Length; i++)
                Console.Error.Write("{0} ", (int)s[i]);
            Console.Error.WriteLine();
            Console.Error.WriteLine();
        }
        */

        public static string ll_os_read(int fd, long count)
        {
            return ll_os_read(fd, (int)count);
        }

        public static string ll_os_read(int fd, int count)
        {
            return getfd(fd).Read(count);
        }

        public static Record_Stat_Result ll_os_stat(string path)
        {
            if (path == "")
                raise_OSError(Errno.ENOENT, "No such file or directory: ''");

            FileInfo f;
            try {
                f = new FileInfo(path);
            }
            catch(System.ArgumentException e) {
                raise_OSError(Errno.EINVAL, e.Message);
                return null;
            }
            catch(System.NotSupportedException e) {
                raise_OSError(Errno.EINVAL, e.Message);
                return null;
            }
            catch(System.IO.IOException e) {
                raise_OSError(Errno.EINVAL, e.Message);
                return null;
            }

            if (f.Exists) {
                Record_Stat_Result res = new Record_Stat_Result();
                TimeSpan t = File.GetLastWriteTime(path) - new DateTime(1970, 1, 1);
                res.item0 ^= S_IFREG;
                res.item6 = (int)f.Length;
                res.item8 = (int)t.TotalSeconds;
                return res;
            }

            DirectoryInfo d = new DirectoryInfo(path);
            if (d.Exists) {
                Record_Stat_Result res = new Record_Stat_Result();
                res.item0 ^= S_IFDIR;
                return res;
            }
            // path is not a file nor a dir, raise OSError
            raise_OSError(Errno.ENOENT, string.Format("No such file or directory: '{0}'", path));
            return null; // never reached
        }

        public static Record_Stat_Result ll_os_fstat(int fd)
        {
            FileStream stream = getfd(fd).GetStream();
            return ll_os_stat(stream.Name);    // TODO: approximate only
        }

        public static Record_Stat_Result ll_os_lstat(string path)
        {
            return ll_os_stat(path);    // TODO
        }

        public static void ll_os_unlink(string path)
        {
            File.Delete(path);
        }

        public static void ll_os_putenv(string key, string value)
        {
            Environment.SetEnvironmentVariable(key, value);
        }

        public static string ll_os_getenv(string key)
        {
            return Environment.GetEnvironmentVariable(key);
        }

        public static void ll_os_unsetenv(string s)
        {
            Environment.SetEnvironmentVariable(s, null);
        }

        public static pypy.runtime.List<Record_String_String> ll_os_envitems()
        {
            pypy.runtime.List<Record_String_String> env = new pypy.runtime.List<Record_String_String>();
            foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
                {
                    Record_String_String var = new Record_String_String();
                    var.item0 = (string)entry.Key;
                    var.item1 = (string)entry.Value;
                    env.Add(var);
                }
            return env;
        }

        public static pypy.runtime.List<string> ll_os_envkeys()
        {
            pypy.runtime.List<string> keys = new pypy.runtime.List<string>();
            foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
                keys.Add((string)entry.Key);
            return keys;
        }
     
        public static long ll_os_lseek(int fd, long offset, int whence)
        {
            SeekOrigin origin = SeekOrigin.Begin;
            switch(whence)
                {
                case 0:
                    origin = SeekOrigin.Begin;
                    break;
                case 1:
                    origin = SeekOrigin.Current;
                    break;
                case 2:
                    origin = SeekOrigin.End;
                    break;
                }
            FileStream stream = getfd(fd).GetStream();
            return stream.Seek(offset, origin);
        }

        public static void ll_os__exit(int x)
        {
            Console.Error.WriteLine("WARNING: ll_os__exit has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static void ll_os_chdir(string s)
        {
            Console.Error.WriteLine("WARNING: ll_os_chdir has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static void ll_os_chmod(string s, int x)
        {
            Console.Error.WriteLine("WARNING: ll_os_chmod has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static int ll_os_dup(int x)
        {
            Console.Error.WriteLine("WARNING: ll_os_dup has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return -1;
        }

        public static void ll_os_dup2(int x, int y)
        {
            Console.Error.WriteLine("WARNING: ll_os_dup2 has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static int ll_os_fork()
        {
            Console.Error.WriteLine("WARNING: ll_os_fork has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return -1;
        }

        public static void ll_os_ftruncate(int x, int y)
        {
            Console.Error.WriteLine("WARNING: ll_os_ftruncate has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static int ll_os_getpid()
        {
            Console.Error.WriteLine("WARNING: ll_os_getpid has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return -1;
        }

        public static bool ll_os_isatty(int x)
        {
            // XXX: this is not the right behaviour, but it's needed
            // to have the interactive interpreter working
            if (x == 0 || x == 1 || x == 2)
                return true;
            else
                return false;
        }

        public static void ll_os_link(string s1, string s2)
        {
            Console.Error.WriteLine("WARNING: ll_os_link has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static void ll_os_mkdir(string s, int x)
        {
            Console.Error.WriteLine("WARNING: ll_os_mkdir has been called, but it's only a stub");
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static pypy.runtime.List<string> ll_os_listdir(string path)
        {
            if (path == "")
                Helpers.raise_OSError(Errno.ENOENT);

            DirectoryInfo dir = new DirectoryInfo(path);
            if (!dir.Exists)
                Helpers.raise_OSError(Errno.ENOENT);

            pypy.runtime.List<string> names = new pypy.runtime.List<string>();
            foreach(DirectoryInfo d in dir.GetDirectories())
                names.Add(d.Name);
            foreach(FileInfo f in dir.GetFiles())
                names.Add(f.Name);

            return names;
        }

        /* XXX old interface, will be removed at some point */
        public static object ll_os_opendir(string path)
        {
            if (path == "")
                Helpers.raise_OSError(Errno.ENOENT);

            DirectoryInfo dir = new DirectoryInfo(path);
            if (!dir.Exists)
                Helpers.raise_OSError(Errno.ENOENT);

            System.Collections.Generic.List<string> names = new System.Collections.Generic.List<string>();
            foreach(DirectoryInfo d in dir.GetDirectories())
                names.Add(d.Name);
            foreach(FileInfo f in dir.GetFiles())
                names.Add(f.Name);

            return names.GetEnumerator();
        }

        /* XXX old interface, will be removed at some point */
        public static string ll_os_readdir(object obj)
        {
            IEnumerator<string> names = (IEnumerator<string>)obj;
            if (names.MoveNext())
                return names.Current;
            else
                return null;
        }

        /* XXX old interface, will be removed at some point */
        public static void ll_os_closedir(object obj)
        {
        }

        public static string posix__getfullpathname(string path)
        {
            return System.IO.Path.GetFullPath(path);
        }

        public static Record_Signed_Signed ll_os_pipe()
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return null;
        }

        public static string ll_os_readlink(string s)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return null;
        }

        public static void ll_os_rename(string s1, string s2)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static void ll_os_rmdir(string s)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static void ll_os_symlink(string s1, string s2)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
        }

        public static int ll_os_system(string s)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return -1;
        }

        public static Record_Signed_Signed ll_os_waitpid(int x, int y)
        {
            Helpers.raise_OSError(Errno.EPERM); // this is only a stub
            return null;
        }
    }
}
