using System;

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
        public int length()
        {
            return this.Count;
        }

        public void append(T item)
        {
            this.Add(item);
        }

        public T getitem_nonneg(int index)
        {
            return this[index];
        }

        public void setitem_nonneg(int index, T value_)
        {
            this[index] = value_;
        }

        public void extend(List<T> other)
        {
            this.AddRange(other);
        }

        public void remove_range(int start, int count)
        {
            this.RemoveRange(start, count);
        }

    }
}
