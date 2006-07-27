using System.IO;
using Mono.Unix;
using Mono.Unix.Native;
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
            OpenFlags f = NativeConvert.ToOpenFlags(flag);
            FilePermissions perm = NativeConvert.ToFilePermissions((uint)mode);
            return Syscall.open(name, f, perm);
        }

        public static void ll_os_close(int fd)
        {
            Syscall.close(fd);
        }

        public static int ll_os_write(int fd, string buffer)
        {
            // TODO: this is very inefficient
            UnixStream fs = new UnixStream (fd);
            StreamWriter w = new StreamWriter(fs);
            w.Write(buffer);
            w.Flush();
            return buffer.Length;
        }

        public static string ll_os_read(int fd, long count)
        {
            return ll_os_read(fd, (int)count);
        }

        public static string ll_os_read(int fd, int count)
        {
            UnixStream fs = new UnixStream (fd);
            StreamReader r = new StreamReader(fs);
            char[] buf = new char[count];
            int n = r.Read(buf, 0, count);
            return new string(buf, 0, n);
        }

        public static Record_Stat_Result ll_os_stat(string path)
        {
            Record_Stat_Result res = new Record_Stat_Result();

            Stat st = new Stat();
            int errno = Syscall.stat(path, out st);
            // assert errno == 0 // TODO: raise exception if != 0            
            res.item0 = (int)st.st_mode;
            res.item1 = (int)st.st_ino;
            res.item2 = (int)st.st_dev;
            res.item3 = (int)st.st_nlink;
            res.item4 = (int)st.st_uid;
            res.item5 = (int)st.st_gid;
            res.item6 = (int)st.st_size;
            res.item7 = (int)st.st_atime;
            res.item8 = (int)st.st_mtime;
            res.item9 = (int)st.st_ctime;
            return res;
        }
    }
}
