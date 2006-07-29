using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;
using pypy.runtime;

namespace pypy.builtin
{
    public class ll_os
    {
        private static Dictionary<int, FileStream> FileDescriptors = new Dictionary<int, FileStream>();
        private static int fdcount = 2; // 0, 1 and 2 are already used by stdin, stdout and stderr
        private const int O_RDONLY = 0;
        private const int O_WRONLY = 1;
        private const int O_RDWR = 2;
        private const int O_CREAT = 64;
        private const int O_APPEND = 1024;

        private const int S_IFMT = 61440;
        private const int S_IFDIR = 16384;
        private const int S_IFREG = 32768;

        public static string ll_os_getcwd()
        {
            return System.IO.Directory.GetCurrentDirectory();
        }

        public static int ll_os_open(string name, int flag, int mode)
        {
            FileAccess f_access = FileAccess.Read;
            FileMode f_mode = FileMode.Open;
            Console.Error.WriteLine("ll_os_open {0}", flag);
            if ((flag & O_RDWR) != 0) {
                throw new ApplicationException("Read/Write mode is not supported, yet");
            }
            else if ((flag & O_WRONLY) != 0) {
                f_access = FileAccess.Write;
                if ((flag & O_APPEND) != 0)
                    f_mode = FileMode.Append;
                else
                    f_mode = FileMode.Create;
            }
            else {
                f_access = FileAccess.Read;
                if ((flag & O_CREAT) != 0)
                    f_mode = FileMode.OpenOrCreate;
                else
                    f_mode = FileMode.Open;
            }
            fdcount++;
            FileDescriptors[fdcount] = new FileStream(name, f_mode, f_access);
            return fdcount;
        }

        public static void ll_os_close(int fd)
        {
            FileStream stream = FileDescriptors[fd];
            Debug.Assert(stream != null);
            stream.Close();
            FileDescriptors.Remove(fd);
        }

        public static int ll_os_write(int fd, string buffer)
        {
            if (fd == 1)
                Console.Write(buffer);
            else if (fd == 2)
                Console.Error.Write(buffer);
            else {
                FileStream stream = FileDescriptors[fd];
                Debug.Assert(stream != null);
                StreamWriter w = new StreamWriter(stream);
                w.Write(buffer);
                w.Flush();
            }
            return buffer.Length;
        }

        public static string ll_os_read(int fd, long count)
        {
            return ll_os_read(fd, (int)count);
        }

        public static string ll_os_read(int fd, int count)
        {
            TextReader reader;
             if (fd == 0)
                 reader = Console.In;
             else {
                 FileStream stream = FileDescriptors[fd];
                 Debug.Assert(stream != null);
                 reader = new StreamReader(stream);
             }
             char[] buf = new char[count];
             int n = reader.Read(buf, 0, count);
             return new string(buf, 0, n);
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
            // TODO: path is not a file nor a dir, should raise OSError
            return null;
        }
    }
}
