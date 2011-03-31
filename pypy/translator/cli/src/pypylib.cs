using System;
using System.Collections.Generic;
using System.Runtime.Serialization.Formatters.Binary;
using System.Runtime.Serialization;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
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
        public static string ToPython(short x)  { return x.ToString(); }
        // XXX: it does not support strings containing "'".
        public static string ToPython(string x) { 
            if (x == null)
                return "None";
            else {
                string res = "";
                foreach(char ch in x)
                    if (ch >= 32 && ch < 128)
                        res+= ch;
                    else
                        res+= string.Format("\\x{0:X2}", (int)ch);
                return string.Format("'{0}'", res);
            }
        }

        public static string ToPython_unicode(string x) { return "u" + ToPython(x); }
        public static string ToPython_unicode(char x)   { return "u" + ToPython(x); }

        public static string ToPython(object x) {
            if (x == null)
                return "None";
            else if (x is Array)
                return ArrayToPython((Array)x);
            else
                return x.ToString();
        }

        private static string ArrayToPython(Array array)
        {
            string res = "[";
            foreach(object item in array) {
                if (item != null && item.GetType() == typeof(string)) {
                    object tmp = (object)item;
                    res += ToPython((string)tmp) + ",";
                }
                else if (item.GetType() == typeof(char)) {
                    object tmp = (object)item;
                    res += pypy.test.Result.ToPython((char)tmp) + ",";
                } 
                else
                    res += ToPython(item) + ",";
                
            }
            res += "]";
            return res;
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

    public class Convert {
        public static double ToDouble(string s)
        {
            if (s == "inf")
                return Double.PositiveInfinity;
            else if (s == "-inf")
                return Double.NegativeInfinity;
            else if (s == "nan")
                return Double.NaN;
            else {
                System.Globalization.NumberFormatInfo formatter;
                formatter = new System.Globalization.NumberFormatInfo();
                formatter.NumberDecimalSeparator = ".";
                return System.Convert.ToDouble(s, formatter);
            }
        }
    }

    public delegate double DelegateType_int__0();
    public delegate double DelegateType_double__double_1(double a);
    public delegate double DelegateType_double_int_double(int a, double b);
    public delegate void DelegateType_void_int_1(int a);
    public delegate bool DelegateType_bool_bool_1(bool a);
    public delegate char DelegateType_char_char_1(char a);
    public delegate int DelegateType_int__int_1(int a);
    public delegate int DelegateType_int__int_2(int a, int b);
    public delegate int DelegateType_int__int_3(int a, int b, int c);
    public delegate int DelegateType_int__int_5(int a, int b, int c, int d, int e);
    public delegate int DelegateType_int__int_27(int a0, int a1, int a2, int a3, int a4, int a5, int a6, int a7, int a8, int a9, int a10, int a11, int a12, int a13, int a14, int a15, int a16, int a17, int a18, int a19, int a20, int a21, int a22, int a23, int a24, int a25, int a26);
    public delegate int DelegateType_int__int_100(int a0, int a1, int a2, int a3, int a4, int a5, int a6, int a7, int a8, int a9, int a10, int a11, int a12, int a13, int a14, int a15, int a16, int a17, int a18, int a19, int a20, int a21, int a22, int a23, int a24, int a25, int a26, int a27, int a28, int a29, int a30, int a31, int a32, int a33, int a34, int a35, int a36, int a37, int a38, int a39, int a40, int a41, int a42, int a43, int a44, int a45, int a46, int a47, int a48, int a49, int a50, int a51, int a52, int a53, int a54, int a55, int a56, int a57, int a58, int a59, int a60, int a61, int a62, int a63, int a64, int a65, int a66, int a67, int a68, int a69, int a70, int a71, int a72, int a73, int a74, int a75, int a76, int a77, int a78, int a79, int a80, int a81, int a82, int a83, int a84, int a85, int a86, int a87, int a88, int a89, int a90, int a91, int a92, int a93, int a94, int a95, int a96, int a97, int a98, int a99);

    public class DummyClass {
        public static object myfield;
    }

}

namespace pypy.runtime
{

    public delegate void LoopDelegate(InputArgs args);

    public class InputArgs {
      public int[] ints = new int[256];
      public double[] floats = new double[256];
      public object[] objs = new object[256];
      public object exc_value = null;
      public int failed_op = -1;

      public int get_int(int i)
      {
        return ints[i];
      }

      public void set_int(int i, int n)
      {
        ints[i] = n;
      }

      public double get_float(int i)
      {
        return floats[i];
      }

      public void set_float(int i, double n)
      {
        floats[i] = n;
      }

      public object get_obj(int i)
      {
        return objs[i];
      }

      public void set_obj(int i, object o)
      {
        objs[i] = o;
      }

      public object get_exc_value()
      {
        return exc_value;
      }

      public void set_exc_value(object v)
      {
        exc_value = v;
      }

      public int get_failed_op()
      {
        return failed_op;
      }

      public void ensure_ints(int n)
      {
        if (ints.Length < n)
          ints = new int[n];
      }

      public void ensure_floats(int n)
      {
        if (floats.Length < n)
          floats = new double[n];
      }

      public void ensure_objs(int n)
      {
        if (objs.Length < n)
          objs = new object[n];

      }
    }

  /*
    public delegate uint FlexSwitchCase(uint block, InputArgs args);

    // XXX: there is a lot of code duplication between the next three classes,
    // but it's hard to share the code in a way that it's both efficient and
    // supported by gencli
    public class MethodIdMap
    { 
      public FlexSwitchCase[] cases = new FlexSwitchCase[4];

      public void add_case(int method_id, FlexSwitchCase c)
      {
        if (cases.Length <= method_id)
          grow();
        cases[method_id] = c;
      }

      public uint jumpto(uint blockid, InputArgs args)
      {
        uint method_id = (blockid & 0xFFFF0000) >> 16;
        return cases[method_id](blockid, args);
      }

      private void grow()
      {
        int newsize = cases.Length * 2;
        FlexSwitchCase[] newcases = new FlexSwitchCase[newsize];
        Array.Copy(cases, newcases, cases.Length);
        cases = newcases;
      }
    }

    public class BaseLowLevelFlexSwitch
    {
        public uint default_blockid = 0xFFFFFFFF;
        public void set_default_blockid(uint blockid)
        {
            this.default_blockid = blockid;
        }
    }

    public class IntLowLevelFlexSwitch: BaseLowLevelFlexSwitch
    {
        public int numcases = 0;
        public int[] values = new int[4];
        public FlexSwitchCase[] cases = new FlexSwitchCase[4];

        public void add_case(int value, FlexSwitchCase c)
        {
            if (numcases >= values.Length)
                grow();
            values[numcases] = value;
            cases[numcases] = c;
            numcases++;
        }

        private void grow()
        {
            int newsize = values.Length * 2;
            int[] newvalues = new int[newsize];
            Array.Copy(values, newvalues, values.Length);
            values = newvalues;
            
            FlexSwitchCase[] newcases = new FlexSwitchCase[newsize];
            Array.Copy(cases, newcases, cases.Length);
            cases = newcases;
        }
        
        public uint execute(int value, InputArgs args)
        {
            for(int i=0; i<numcases; i++)
              if (values[i] == value) {
                  // 0 stands for "the first block of the function", see the comment
                  // in rgenop.FlexCaseMethod.emit_preamble
                  return cases[i](0, args); 
                }
            return default_blockid;
        }
    }

    public class ObjectLowLevelFlexSwitch: BaseLowLevelFlexSwitch
    {
        public int numcases = 0;
        public object[] values = new object[4];
        public FlexSwitchCase[] cases = new FlexSwitchCase[4];

        public void add_case(object value, FlexSwitchCase c)
        {
            if (numcases >= values.Length)
                grow();
            values[numcases] = value;
            cases[numcases] = c;
            numcases++;
        }

        private void grow()
        {
            int newsize = values.Length * 2;
            object[] newvalues = new object[newsize];
            Array.Copy(values, newvalues, values.Length);
            values = newvalues;
            
            FlexSwitchCase[] newcases = new FlexSwitchCase[newsize];
            Array.Copy(cases, newcases, cases.Length);
            cases = newcases;
        }
        
        public uint execute(object value, InputArgs args)
        {
            for(int i=0; i<numcases; i++)
              if (values[i] == value) {
                  // 0 stands for "the first block of the function", see the comment
                  // in rgenop.FlexCaseMethod.emit_preamble
                  return cases[i](0, args); 
                }
            return default_blockid;
        }
    }
  */
        
    public class DelegateHolder
    {
        public LoopDelegate func;

        // we need getter and setter because we can't directly access fields from RPython
        public void SetFunc(LoopDelegate func)
        {
            this.func = func;
        }

        public LoopDelegate GetFunc()
        {
            return this.func;
        }
    }



    public class AutoSaveAssembly
    {
        private AssemblyBuilder assembly;
        private bool saved = false;
        private string name;

        public static AutoSaveAssembly Create(string name)
        {
            return new AutoSaveAssembly(name);
        }

        public AutoSaveAssembly(string name)
        {
            this.name = name;
            AssemblyName assemblyName = new AssemblyName(); 
            assemblyName.Name = name;
            this.assembly = AppDomain.CurrentDomain.DefineDynamicAssembly(assemblyName, AssemblyBuilderAccess.RunAndSave);
        }

        public void Save()
        {
            if (this.saved)
                return;
            this.assembly.Save(this.name);
            this.saved = true;
        }

        ~AutoSaveAssembly()
        {
            this.Save();
        }

        public AssemblyBuilder GetAssemblyBuilder()
        {
            return this.assembly;
        }

        public static TypeBuilder DefineType(ModuleBuilder module, string name)
        {
            return module.DefineType(name,
                                     TypeAttributes.Public |
                                     TypeAttributes.Class);
        }

        public static MethodBuilder DefineMethod(TypeBuilder typeBuilder, string name, Type res, Type[] args)
        {
            return typeBuilder.DefineMethod("invoke",
                                            MethodAttributes.HideBySig | 
                                            MethodAttributes.Static | 
                                            MethodAttributes.Public, 
                                            res, 
                                            args);
        }

        
    }

    public class Utils
    {

        public static DynamicMethod CreateDynamicMethod(string name, Type res, Type[] args)
        {
            return new DynamicMethod(name, res, args, typeof(Utils).Module);
        }

        // if you call il.Emit(OpCodes.Ldc_R8, mydouble) from pythonnet, it
        // selects the wrong overload. To work around it, we call it from C# and
        // live happy
        public static void Emit_Ldc_R8(ILGenerator il, double val) 
        {
            il.Emit(OpCodes.Ldc_R8, val);
        }

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

        public static string OOString(uint n, int base_)
        {
            if (base_ == -1)
                base_ = 10;
            return Convert.ToString(n, base_);
        }

        public static string OOString(long n, int base_)
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
          if (obj == null)
            return "<null object>";
          else
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

        private static void check_ascii(char ch)
        {
            if ((int)ch > 127)
                Helpers.raise_UnicodeDecodeError();
        }

        public static string OOUnicode(char ch)
        {
            return ch.ToString();
        }

        public static string OOUnicode(string s)
        {
            foreach(char ch in s)
                check_ascii(ch);
            return s;
        }

        public static int OOParseInt(string s, int base_)
        {
            return Convert.ToInt32(s, base_);
        }

        public static double OOParseFloat(string s)
        {
            try {
                return Double.Parse(s.Trim());
            }
            catch(FormatException e) {
                Helpers.raise_ValueError();
                return -1;
            }
        }

        public static bool Equal<T>(T t1, T t2) 
        { 
            if (t1 == null)
              return (t2 == null);
            else
              return t1.Equals(t2);
        }

        public static int GetHashCode<T>(T obj)
        {
            if (obj == null)
              return 0;
            else
              return obj.GetHashCode();
        }

        public static void throwInvalidBlockId(uint blockid)
        {
            uint method_id = (blockid & 0xFFFF0000) >> 16;
            uint block_num = (blockid & 0x0000FFFF);
            string msg = string.Format("Invalid block id: 0x{0:X} ({1}, {2})", 
                                       blockid, method_id, block_num);
            throw new Exception(msg);
        }

        public static void Serialize(object obj, string filename)
        {
            FileStream fs = new FileStream(filename, FileMode.Create);
            BinaryFormatter formatter = new BinaryFormatter();
            try {
                formatter.Serialize(fs, obj);
            }
            catch (SerializationException e) {
                Console.Error.WriteLine("Failed to serialize. Reason: " + e.Message);
                throw;
            }
            finally {
                fs.Close();
            }
        }

        public static object Deserialize(string filename)
        {
            FileStream fs = null;
            try {
                fs = new FileStream(filename, FileMode.Open);
                BinaryFormatter formatter = new BinaryFormatter();
                return formatter.Deserialize(fs);
            }
            catch (FileNotFoundException e) {
                return null;
            }
            catch (SerializationException e) {
                Console.Error.WriteLine("Failed to deserialize. Reason: " + e.Message);
                return null;
            }
            finally {
                if (fs != null)
                    fs.Close();
            }
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
        public static int ll_hash(string s)
        {
            return s.GetHashCode();
        }
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
            return string.Compare(s1, s2, StringComparison.Ordinal);
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

        public static int ll_count(string s1, string s2, int start, int stop)
        {
            if (stop > s1.Length)
                stop = s1.Length;
            if (s2.Length == 0)
            {
                if ((stop-start) < 0)
                {
                    return 0;
                }
                return stop - start + 1;
            }
            int result = 0;
            int i = start;
            while (true)
            {
                int pos = ll_find(s1, s2, i, stop);
                if (pos < 0)
                    return result;
                result += 1;
                i = pos + s2.Length;
            }
        }

        public static int ll_count_char(string s1, char c, int start, int stop)
        {
            if (stop > s1.Length)
                stop = s1.Length;
            int result = 0;
            for (int i=start; i < stop; i++) {
                if (s1[i] == c)
                    result += 1;
            }
            return result;
        }


        public static int ll_rfind(string s1, string s2, int start, int stop)
        {
            if (stop > s1.Length)
                stop = s1.Length;
            int count = stop-start;
            if (start > s1.Length)
                return -1;
            if (s2 == "")
              return stop;
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
            if (start > s.Length || stop == 0)
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

        public static string[] ll_split_chr(string s, char ch, int max)
        {
            if (max < 0)
                return s.Split(ch);
            else
                return s.Split(new Char[] {ch}, max + 1);
        }

        public static string[] ll_rsplit_chr(string s, char ch, int max)
        {
            string[] splits = s.Split(ch);
            if (max < 0 || splits.Length <= max + 1)
                return splits;
            else {
                /* XXX not very efficient */
                string first = splits[0];
                // join the first (length - max - 1) items
                int i;
                for (i = 1; i < splits.Length - max; i++)
                    first += ch + splits[i];
                splits[0] = first;
                Array.Copy(splits, i, splits, 1, max);
                Array.Resize(ref splits, max + 1);
                return splits;
            }
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

        public List(int capacity): base(capacity)
        {
        }

        public override string ToString()
        {
            // TODO: use StringBuilder instead
            string res = "[";
            foreach(T item in this) {
                if (item.GetType() == typeof(string)) {
                    object tmp = (object)item;
                    res += pypy.test.Result.ToPython((string)tmp) + ",";
                }
                else if (item.GetType() == typeof(char)) {
                    object tmp = (object)item;
                    res += pypy.test.Result.ToPython((char)tmp) + ",";
                }                  
                else
                    res += pypy.test.Result.ToPython(item) + ",";
            }
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

        public ListOfVoid() { }
        public ListOfVoid(int capacity) { }

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
        IEqualityComparer<TKey> comparer = null;
        TValue cache;

        public Dict() {}
        public Dict(IEqualityComparer<TKey> comparer): base(comparer) 
        { 
            this.comparer = comparer;
        }

        public int ll_length() { return this.Count; }
        public TValue ll_get(TKey key) { return cache; }
        public void ll_set(TKey key, TValue value) { this[key] = value; }
        public bool ll_remove(TKey key) { return this.Remove(key); }
        public bool ll_contains(TKey key) { return this.TryGetValue(key, out cache); }
        public void ll_clear() { this.Clear(); }

        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            return new DictItemsIterator<TKey, TValue>(this);
        }

        // XXX: this is CustomDict specific, maybe we should have a separate class for it
        public Dict<TKey, TValue> ll_copy()
        {
            Dict<TKey, TValue> res = new Dict<TKey, TValue>(comparer);
            foreach(KeyValuePair<TKey, TValue> item in this)
                res[item.Key] = item.Value;
            return res;
        }
    }

    // it assumes TValue is a placeholder, it's not really used
    public class DictOfVoid<TKey, TValue>: System.Collections.Generic.Dictionary<TKey, TValue>
    {
        IEqualityComparer<TKey> comparer = null;

        public DictOfVoid() {}
        public DictOfVoid(IEqualityComparer<TKey> comparer): base(comparer)
        {
            this.comparer = comparer;
        }

        public int ll_length() { return this.Count; }
        public void ll_get(TKey key) { }
        public void ll_set(TKey key) { this[key] = default(TValue); }
        public bool ll_remove(TKey key) { return this.Remove(key); }
        public bool ll_contains(TKey key) { return this.ContainsKey(key); }
        public void ll_contains_get() { }
        public void ll_clear() { this.Clear(); }

        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            return new DictItemsIterator<TKey, TValue>(this);
        }

        public DictOfVoid<TKey, TValue> ll_copy() // XXX: why it should return a Dict?
        {
            DictOfVoid<TKey, TValue> res = new DictOfVoid<TKey, TValue>(comparer);
            foreach(KeyValuePair<TKey, TValue> item in this)
                res[item.Key] = item.Value;
            return res;            
        }
    }

    // it assumes TKey is a placeholder, it's not really used
    public class DictOfVoidKey<TKey, TValue>
    {
        private int length = 0;
        private TValue elem = default(TValue);

        public DictOfVoidKey() {}
        public DictOfVoidKey(IEqualityComparer<TKey> comparer) {}

        public int ll_length() { return this.length; }
        public TValue ll_get() { return this.elem; }
        
        public void ll_set(TValue value) { 
            this.length = 1;
            this.elem = value;
        }

        public bool ll_remove() {
            if (this.length > 0) {
                this.length = 0;
                return true;
            }
            return false;
        }

        public bool ll_contains() { return (this.length > 0); }
        public void ll_contains_get() { }
        public void ll_clear() { this.length = 0; }

        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            Dictionary<TKey, TValue> foo = new Dictionary<TKey, TValue>();
            if (length == 1)
                foo[default(TKey)] = this.elem;
            return new DictItemsIterator<TKey, TValue>(foo);
        }
    }

    public class DictVoidVoid
    {
        private int length = 0;

        public int ll_length() { return length; }
        public void ll_get() { }
        public void ll_set() { length = 1; }
        public bool ll_remove() { 
            if (length == 0)
                return false;
            length = 0;
            return true;
        }
        public bool ll_contains() { return length != 0; }
        public void ll_contains_get() { }
        public void ll_clear() { length = 0; }

        public DictItemsIterator<int, int> ll_get_items_iterator()
        {
            Dictionary<int, int> foo = new Dictionary<int, int>();
            if (length == 1)
                foo[0] = 0;
            return new DictItemsIterator<int, int>(foo);
        }
    }

    public class DictItemsIterator<TKey, TValue>
    {
        Dictionary<TKey, TValue> dict;
        int size;
        TKey[] keys;
        int pos;

        public DictItemsIterator(Dictionary<TKey, TValue> dict)
        {
            this.dict = dict;
            this.size = dict.Count;
            this.keys = new TKey[this.size];
            dict.Keys.CopyTo(this.keys, 0);
            this.pos = -1;
        }

        public bool ll_go_next() { 
            if (this.size != this.dict.Count)
                Helpers.raise_RuntimeError();
            if (this.pos >= this.size-1)
                return false;
            pos++;
            return true;
        }

        public TKey ll_current_key() { 
            return this.keys[this.pos]; 
        }

        public TValue ll_current_value() { 
            TKey key = this.ll_current_key();
            return this.dict[key];
        }
    }

    public class WeakReference
    {
        System.WeakReference wref;

        public void ll_set(object obj)
        {
            this.wref = new System.WeakReference(obj);
        }

        public object ll_deref()
        {
            return this.wref.Target;
        }
    }

    public class Record_Signed_Signed {
        public int item0;
        public int item1;
        public override string ToString() { return string.Format("({0}, {1},)", item0, item1); }
        public override bool Equals(object obj)
        {
            Record_Signed_Signed x = (Record_Signed_Signed)obj;
            return item0 == x.item0 && item1 == x.item1;
        }
        public override int GetHashCode() { return item0.GetHashCode(); }
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

    public class Record_String_String {
        public string item0;
        public string item1;
        public override string ToString() { return string.Format("({0}, {1},)", item0, item1); }
        public override bool Equals(object obj)
        {
            Record_String_String x = (Record_String_String)obj;
            return item0 == x.item0 && item1 == x.item1;
        }
        public override int GetHashCode() { return item0.GetHashCode(); }
    }

    public class Record_Stat_Result {
        public int item0, item3, item4, item5;
        public long item1, item2, item6;
        public double item7, item8, item9;
        public override string ToString() 
        { 
            return string.Format("({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9},)", 
                                 item0, item1, item2, item3, item4, 
                                 item5, item6, item7, item8, item9);
        }
        public override bool Equals(object obj)
        {
            Record_Stat_Result x = (Record_Stat_Result)obj;
            return item0 == x.item0 && item1 == x.item1 && item2 == x.item2 
                && item3 == x.item3 && item4 == x.item4 && item5 == x.item5
                && item6 == x.item6 && item7 == x.item7 && item8 == x.item8
                && item9 == x.item9;
        }
        public override int GetHashCode() { return item0.GetHashCode(); }
    }
}

namespace pypy.builtin
{
    public class ll_strtod
    {
        public static string ll_strtod_formatd(string format, double d)
        {
            // XXX: this is really a quick hack to make things work.
            // it should disappear, because this function is not
            // supported by ootypesystem.
            return d.ToString(); // XXX: we are ignoring "format"
        }
    }

    public class ll_time
    {
        public static double ll_time_time()
        {
            TimeSpan t = (DateTime.UtcNow - new DateTime(1970, 1, 1));
            return t.TotalSeconds;
        }

        public static double ll_time_clock()
        {
          return DateTime.UtcNow.Ticks * 1e-7;
        }

        public static void ll_time_sleep(double seconds)
        {
            System.Threading.Thread.Sleep((int)(seconds*1000));
        }
    }

    public class rffi
    {
      public static int tolower(int chr)
      {
        return (int)Char.ToLower((char)chr);
      }
    }

}
