using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using pypy.runtime;

namespace pypy.test
{
    public class Result 
    {
        public static string ToPython(int x)    { return x.ToString(); }
        public static string ToPython(bool x)   { return x.ToString(); }
        public static string ToPython(double x) { return string.Format("{0:F8}", x); }
        public static string ToPython(char x)   { return string.Format("'{0}'", x);  }
        public static string ToPython(uint x)   { return x.ToString(); }
        public static string ToPython(long x)   { return x.ToString(); }
        public static string ToPython(ulong x)  { return x.ToString(); }
        // XXX: it does not support strings containing "'".
        public static string ToPython(string x) { 
            if (x == null)
                return "None";
            else
                return string.Format("'{0}'", x); 
        }

        public static string ToPython(object x) {
            if (x == null)
                return "None";
            else
                return x.ToString();
        }

        public static string InstanceToPython(object obj) 
        { 
            return string.Format("InstanceWrapper('{0}')", obj.GetType().FullName);
        }

        public static string FormatException(object obj) 
        { 
            return string.Format("ExceptionWrapper('{0}')", obj.GetType().FullName);
        }
    }
}

namespace pypy.runtime
{
    public class Utils
    {
        public static object RuntimeNew(Type t)
        {
            return t.GetConstructor(new Type[0]).Invoke(new object[0]);
        }

        public static bool SubclassOf(Type a, Type b)
        {
            return (a == b || a.IsSubclassOf(b));
        }

        public static string OOString(int n, int base_)
        {
            if (base_ == -1)
                base_ = 10;
            if (n<0 && base_ != 10)
                return "-" + Convert.ToString(-n, base_);
            else
                return Convert.ToString(n, base_);
        }

        public static string OOString(double d, int base_)
        {
            return d.ToString();
        }

        public static string OOString(object obj, int base_)
        {
            return string.Format("<{0} object>", obj.GetType().FullName);
        }

        public static string OOString(char ch, int base_)
        {
            return ch.ToString();
        }

        public static string OOString(string s, int base_)
        {
            return s;
        }

        public static string OOString(bool b, int base_)
        {
            return b.ToString();
        }

        public static int OOParseInt(string s, int base_)
        {
            return Convert.ToInt32(s, base_);
        }

        public static bool Equal<T>(T t1, T t2) 
        { 
            return t1.Equals(t2);
        }

        public static int GetHashCode<T>(T obj)
        {
            return obj.GetHashCode();
        }
    }

    public class StringBuilder
    {
        System.Text.StringBuilder builder = new System.Text.StringBuilder();

        public void ll_allocate(int size) { builder.Capacity = size; }
        public void ll_append_char(char ch) { builder.Append(ch); }
        public void ll_append(string s) { builder.Append(s); }
        public string ll_build() { return builder.ToString(); }
    }

    public class String
    {
        public static char ll_stritem_nonneg(string s, int index)
        {
            return s[index];
        }

        public static int ll_strlen(string s)
        {
            return s.Length;
        }

        public static string ll_strconcat(string s1, string s2)
        {
            return s1+s2;
        }

        public static bool ll_streq(string s1, string s2)
        {
            return s1 == s2;
        }

        public static int ll_strcmp(string s1, string s2)
        {
            return string.Compare(s1, s2);
        }

        public static bool ll_startswith(string s1, string s2)
        {
            return s1.StartsWith(s2);
        }

        public static bool ll_endswith(string s1, string s2)
        {
            return s1.EndsWith(s2);
        }
        
        public static int ll_find(string s1, string s2, int start, int stop)
        {
            if (stop > s1.Length)
                stop = s1.Length;
            int count = stop-start;
            if (start > s1.Length)
                return -1;
            return s1.IndexOf(s2, start, count);
        }

        public static int ll_rfind(string s1, string s2, int start, int stop)
        {
            if (stop > s1.Length)
                stop = s1.Length;
            int count = stop-start;
            if (start > s1.Length)
                return -1;
            return s1.LastIndexOf(s2, stop-1, count);
        }

        public static int ll_find_char(string s, char ch, int start, int stop)
        {
            if (stop > s.Length)
                stop = s.Length;
            int count = stop-start;
            return s.IndexOf(ch, start, count);
        }

        public static int ll_rfind_char(string s, char ch, int start, int stop)
        {
            if (stop > s.Length)
                stop = s.Length;
            int count=stop-start;
            if (start > s.Length)
                return -1;
            return s.LastIndexOf(ch, stop-1, count);
        }

        public static string ll_strip(string s, char ch, bool left, bool right)
        {
            if (left && right)
                return s.Trim(ch);
            else if (left)
                return s.TrimStart(ch);
            else if (right)
                return s.TrimEnd(ch);
            else
                return s;

        }

        public static string ll_upper(string s)
        {
            return s.ToUpper();
        }

        public static string ll_lower(string s)
        {
            return s.ToLower();
        }

        public static string ll_substring(string s, int start, int count)
        {
            return s.Substring(start, count);
        }

        public static List<string> ll_split_chr(string s, char ch)
        {
            List<string> res = new List<string>();
            res.AddRange(s.Split(ch));
            return res;
        }

        public static bool ll_contains(string s, char ch)
        {
            return s.IndexOf(ch) != -1;
        }

        public static string ll_replace_chr_chr(string s, char ch1, char ch2)
        {
            return s.Replace(ch1, ch2);
        }
    }

    //The public interface List must implement is defined in
    // rpython.ootypesystem.ootype.List.GENERIC_METHODS
    public class List<T>: System.Collections.Generic.List<T>
    {
        public List(): base()
        {
        }

        public List(T[] array): base(array)
        {
        }

        public override string ToString()
        {
            // TODO: use StringBuilder instead
            string res = "[";
            foreach(T item in this)
                res += item.ToString() + ","; // XXX: doesn't work for chars
            res += "]";
            return res;
        }

        public int ll_length()
        {
            return this.Count;
        }

        public T ll_getitem_fast(int index)
        {
            return this[index];
        }

        public void ll_setitem_fast(int index, T item)
        {
            this[index] = item;
        }

        public void _ll_resize(int length)
        {
            if (length > this.Count)
                this._ll_resize_ge(length);
            else if (length < this.Count)
                this._ll_resize_le(length);
        }

        public void _ll_resize_ge(int length)
        {
            if (this.Count < length) 
            {
                // TODO: this is inefficient because it can triggers
                // many array resize
                int diff = length - this.Count;
                for(int i=0; i<diff; i++)
                    this.Add(default(T));
            }
        }

        public void _ll_resize_le(int length)
        {
            if (length < this.Count)
            {
                int diff = this.Count - length;
                this.RemoveRange(length, diff);
            }
        }
    }

    public class ListOfVoid
    {
        int Count = 0;

        public override string ToString()
        {
            // TODO: use StringBuilder instead
            string res = "[";
            for(int i=0; i<this.Count; i++)
                res += "None, ";
            res += "]";
            return res;
        }

        public int ll_length() { return this.Count; }
        public void ll_getitem_fast(int index) { }
        public void ll_setitem_fast(int index) { }
        public void _ll_resize(int length) { this.Count = length; }
        public void _ll_resize_ge(int length) { this.Count = length; }
        public void _ll_resize_le(int length) { this.Count = length; }
    }

    public class Dict<TKey, TValue>: System.Collections.Generic.Dictionary<TKey, TValue>
    {
        public int ll_length() { return this.Count; }
        public TValue ll_get(TKey key) { return this[key]; }
        public void ll_set(TKey key, TValue value) { this[key] = value; }
        public bool ll_remove(TKey key) { return this.Remove(key); }
        public bool ll_contains(TKey key) { return this.ContainsKey(key); }
        public void ll_clear() { this.Clear(); }

        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            return new DictItemsIterator<TKey, TValue>(this.GetEnumerator());
        }
    }

    public class DictOfVoid<TKey>: System.Collections.Generic.Dictionary<TKey, int> // int is a placeholder
    {
        public int ll_length() { return this.Count; }
        public void ll_get(TKey key) { }
        public void ll_set(TKey key) { this[key] = 0; }
        public bool ll_remove(TKey key) { return this.Remove(key); }
        public bool ll_contains(TKey key) { return this.ContainsKey(key); }
        public void ll_clear() { this.Clear(); }

        //XXX ll_get_items_iterator is not supported, yet
        /*
        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            return new DictItemsIterator<TKey, TValue>(this.GetEnumerator());
        }
        */
    }

    public class DictVoidVoid
    {
        public int ll_length() { return 0; }
        public void ll_get() { }
        public void ll_set() { }
        public bool ll_remove() { return false; } // should it be true?
        public bool ll_contains() { return false; }
        public void ll_clear() { }

        //XXX ll_get_items_iterator is not supported, yet
        /*
        public DictVoidVoidItemsIterator ll_get_items_iterator()
        {
            return new DictVoidVoidItemsIterator();
        }
        */
    }

    public class DictItemsIterator<TKey, TValue>
    {
        IEnumerator<KeyValuePair<TKey, TValue>> it;

        public DictItemsIterator(IEnumerator<KeyValuePair<TKey, TValue>> it)
        {
            this.it = it;
        }

        public bool ll_go_next() { return it.MoveNext(); }
        public TKey ll_current_key() { return it.Current.Key; }
        public TValue ll_current_value() { return it.Current.Value; }
    }

    public class Record_Float_Signed {
        public double item0;
        public int item1;
        public override string ToString() { return string.Format("({0}, {1},)", item0, item1); }
        public override bool Equals(object obj)
        {
            Record_Float_Signed x = (Record_Float_Signed)obj;
            return item0 == x.item0 && item1 == x.item1;
        }
        public override int GetHashCode() { return item0.GetHashCode(); }
    }

    public class Record_Float_Float {
        public double item0;
        public double item1;
        public override string ToString() { return string.Format("({0}, {1},)", item0, item1); }
        public override bool Equals(object obj)
        {
            Record_Float_Float x = (Record_Float_Float)obj;
            return item0 == x.item0 && item1 == x.item1;
        }
        public override int GetHashCode() { return item0.GetHashCode(); }
    }
}

namespace pypy.builtin
{
    public class Builtin
    {
        public static double ll_time_time()
        {
            TimeSpan t = (DateTime.UtcNow - new DateTime(1970, 1, 1));
            return t.TotalSeconds;
        }

        static DateTime ClockStart = DateTime.UtcNow;
        public static double ll_time_clock()
        {
            return (DateTime.UtcNow - ClockStart).TotalSeconds;
        }

        // XXX: very hackish, refactoring needed
        public static int ll_os_write(int fd, string buffer)
        {
            if (fd == 1 || fd == 2)
                Console.WriteLine(buffer);
            return buffer.Length;
        }

        public static double ll_math_floor(double x)
        {
            return Math.Floor(x);
        }

        public static double ll_math_fmod(double x, double y)
        {
            return Math.IEEERemainder(x, y);
        }

        public static Record_Float_Float ll_math_modf(double x)
        {
            Record_Float_Float result = new Record_Float_Float();
            result.item1 = (long)x; // truncate
            result.item0 = x - result.item1;
            return result;
        }

        // this code is borrowed from 
        // http://web.telia.com/~u31115556/under_construction/Functions.Cephes.CFunctions.cs
        [StructLayout(LayoutKind.Explicit), CLSCompliantAttribute(false)]
        struct DoubleUshorts 
        {
            [FieldOffset(0)] public double d;
            [FieldOffset(0)] public ushort u0;
            [FieldOffset(2)] public ushort u1;
            [FieldOffset(4)] public ushort u2;
            [FieldOffset(6)] public ushort u3;
        }

        public static unsafe Record_Float_Signed ll_math_frexp(double x)
        {
            Record_Float_Signed result = new Record_Float_Signed();
            if (x == 0.0) // Laj: Else pw2 = -1022
            {
                result.item0 = 0.0;
                result.item1 = 0;
                return result;
            }

            DoubleUshorts u;
            u.d = x;

            short *q = (short *)&u.u3;

            int i = (*q >> 4) & 0x7ff;

            i -= 0x3fe;
            result.item1 = i;
            unchecked
            {
                // Constant value '32783' cannot be converted to a 'short'
                *q &= (short)0x800f;
            }
            // Warning: Bitwise-or operator used on a sign-extended operand;
            // consider casting to a smaller unsigned type first
            *q |= 0x3fe0;
            result.item0 = u.d;
            return result;
        }

    }
}
