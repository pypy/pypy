using System;
using System.IO;
using pypy.runtime;

namespace pypy.builtin
{
    public class ll_os_path
    {
        public static string ll_join(string a, string b)
        {
            return Path.Combine(a, b);
        }
    }
}
