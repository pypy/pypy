using System;
using pypy.runtime;

namespace pypy.builtin
{
    public class ll_os
    {
        public static string ll_os_getcwd()
        {
            return System.IO.Directory.GetCurrentDirectory();
        }

        public static int ll_os_open(string name, int flag, int mode)
        {
            //PrebuiltGraphs.raiseOSError(2); // ENOENT
            return -1; // can't be reached
        }

        public static void ll_os_close(int fd)
        {
        }

        public static int ll_os_write(int fd, string buffer)
        {
            if (fd == 1)
                Console.Write(buffer);
            else if (fd == 2)
                Console.Error.Write(buffer);
            else
                throw new ApplicationException(string.Format("Wrong file descriptor: {0}", fd));
            return buffer.Length;
        }

        public static string ll_os_read(int fd, long count)
        {
            return ll_os_read(fd, (int)count);
        }

        public static string ll_os_read(int fd, int count)
        {
             if (fd == 0) {
                 char[] buf = new char[count];
                 int n = Console.In.Read(buf, 0, count);
                 return new string(buf, 0, n);
             }
             else
                 throw new ApplicationException(string.Format("Wrong file descriptor: {0}", fd));
        }

        public static Record_Stat_Result ll_os_stat(string path)
        {
            Record_Stat_Result res = new Record_Stat_Result();
            return res;
        }
    }
}
