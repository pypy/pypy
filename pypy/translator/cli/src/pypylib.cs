using System;
using System.Collections.Generic;

namespace pypy.test
{
    public class Result 
    {
        public static string ToPython(int x)    { return x.ToString(); }
        public static string ToPython(bool x)   { return x.ToString(); }
        public static string ToPython(double x) { return x.ToString(); }
        public static string ToPython(char x)   { return string.Format("'{0}'", x); }
        public static string ToPython(uint x)   { return x.ToString(); }
        public static string ToPython(long x)   { return x.ToString(); }

        public static string ToPython(object obj) 
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
            
    }

    //The public interface List must implement is defined in
    // rpython.ootypesystem.ootype.List.GENERIC_METHODS
    public class List<T>: System.Collections.Generic.List<T>
    {
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

        /*
        public void append(T item)
        {
            this.Add(item);
        }

        public void extend(List<T> other)
        {
            this.AddRange(other);
        }

        public void remove_range(int start, int count)
        {
            this.RemoveRange(start, count);
        }

        public int index(T item)
        {
            return this.IndexOf(item);
        }
        */
    }

    public class Dict<TKey, TValue>: System.Collections.Generic.Dictionary<TKey, TValue>
    {
        public int ll_length()
        {
            return this.Count;
        }

        public TValue ll_get(TKey key)
        {
            return this[key];
        }

        public void ll_set(TKey key, TValue value)
        {
            this[key] = value;
        }

        public bool ll_remove(TKey key)
        {
            return this.Remove(key);
        }

        public bool ll_contains(TKey key)
        {
            return this.ContainsKey(key);
        }

        public void ll_clear()
        {
            this.Clear();
        }

        public DictItemsIterator<TKey, TValue> ll_get_items_iterator()
        {
            return new DictItemsIterator<TKey, TValue>(this.GetEnumerator());
        }
    }

    public class DictItemsIterator<TKey, TValue>
    {
        IEnumerator<KeyValuePair<TKey, TValue>> it;

        public DictItemsIterator(IEnumerator<KeyValuePair<TKey, TValue>> it)
        {
            this.it = it;
        }

        public bool ll_go_next()
        {
            return it.MoveNext();
        }

        public TKey ll_current_key()
        {
            return it.Current.Key;
        }

        public TValue ll_current_value()
        {
            return it.Current.Value;
        }
    }
}
