using System;
using System.IO;
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
            Debug.Assert(writer != null); // XXX: raise OSError?
            writer.Write(buffer);
            writer.Flush();
        }
        
        public string Read(int count)
        {
            Debug.Assert(reader != null); // XXX: raise OSError?
            char[] buf = new char[count];
            int n = reader.Read(buf, 0, count);
            return new string(buf, 0, n);
        }
    }

    class BinaryFile: IFile
    {
        private FileStream stream;
        public BinaryFile(FileStream stream)
        {
            this.stream = stream;
        }

        public FileStream GetStream()
        {
            return stream;
        }
        
        public void Write(string buffer)
        {
            foreach(char ch in buffer)
                stream.WriteByte((byte)ch);
            stream.Flush();
        }

        public string Read(int count)
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
        private const int O_RDONLY = 0;
        private const int O_WRONLY = 1;
        private const int O_RDWR = 2;
        private const int O_CREAT = 64;
        private const int O_TRUNC = 512;
        private const int O_APPEND = 1024;
        private const int O_BINARY = 32768;

        private const int S_IFMT = 61440;
        private const int S_IFDIR = 16384;
        private const int S_IFREG = 32768;

        static ll_os()
        {
            FileDescriptors = new Dictionary<int, IFile>();
            FileDescriptors[0] = new TextFile(null, Console.In, null);
            FileDescriptors[1] = new TextFile(null, null, Console.Out);
            FileDescriptors[2] = new TextFile(null, null, Console.Error);
            fdcount = 2; // 0, 1 and 2 are already used by stdin, stdout and stderr
        }

        public static string ll_os_getcwd()
        {
            return System.IO.Directory.GetCurrentDirectory();
        }

        private static IFile getfd(int fd)
        {
            IFile f = FileDescriptors[fd];
            Debug.Assert(f != null, string.Format("Invalid file descriptor: {0}", fd));
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
            if ((flags & O_TRUNC) !=0 ) return FileMode.Truncate;
            if ((flags & O_CREAT) !=0 ) return FileMode.CreateNew;
            return FileMode.Open;
        }

        public static int ll_os_open(string name, int flags, int mode)
        {
            FileAccess f_access = get_file_access(flags);
            FileMode f_mode = get_file_mode(flags);
            FileStream stream = new FileStream(name, f_mode, f_access);
            IFile f;

            if ((flags & O_BINARY) != 0)
                f = new BinaryFile(stream);
            else {
                StreamWriter writer = null;
                StreamReader reader = null;
                if (f_access == FileAccess.Read || f_access == FileAccess.ReadWrite)
                    reader = new StreamReader(stream);
                if (f_access == FileAccess.Write || f_access == FileAccess.ReadWrite)
                    writer = new StreamWriter(stream);
                f = new TextFile(stream, reader, writer);
            }

            fdcount++;
            FileDescriptors[fdcount] = f;
            return fdcount;
        }

        public static void ll_os_close(int fd)
        {
            FileStream stream = getfd(fd).GetStream();
            stream.Close();
            FileDescriptors.Remove(fd);
        }

        public static int ll_os_write(int fd, string buffer)
        {
            getfd(fd).Write(buffer);
            return buffer.Length;
        }

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
            FileInfo f = new FileInfo(path);
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
            Helpers.raise_OSError(2); // ENOENT
            return null; // never reached
        }

        public static Record_Stat_Result ll_os_fstat(int fd)
        {
            FileStream stream = getfd(fd).GetStream();
            return ll_os_stat(stream.Name);
        }

        public static void ll_os_unlink(string path)
        {
            File.Delete(path);
        }
     
        public static long ll_os_lseek(int fd, int offset, int whence)
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
    }
}
