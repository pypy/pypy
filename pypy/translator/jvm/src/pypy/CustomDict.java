package pypy;

import java.util.AbstractSet;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Iterator;
import java.util.Set;

/**
 * An implementation of the Map interface where the hashcode and 
 * equals methods are supplied in the constructor.  It is backed
 * by a standard Java hashmap, and uses adapter classes to bridge
 * between them.
 * @author Niko Matsakis <niko@alum.mit.edu>
 */
public class CustomDict<K,V> implements Map<K,V>
{
    public final Equals equals;
    public final HashCode hashCode;
    public final Map<Adapter<K>, V> backingMap = 
        new HashMap<Adapter<K>, V>();
    
    public static <K,V> CustomDict<K,V> make(
            final Equals equals, final HashCode hashCode)
    {
        return new CustomDict<K,V>(equals, hashCode);
    }
    
    public CustomDict(final Equals equals, final HashCode hashCode) {
        this.hashCode = hashCode;
        this.equals = equals;
        //System.err.println("Equals: "+equals.getClass());
        //System.err.println("HashCode: "+hashCode.getClass());
    }

    public class Adapter<AK> {
        public final AK object;
        public Adapter(AK object) {
            this.object = object;
        }

        public int hashCode() {
            return hashCode.invoke(this.object);
        }

        public boolean equals(Object other) {
            return equals.invoke(this.object, ((Adapter<?>)other).object);
        }
    }
    
    private <AK> Adapter<AK> w(AK k) {
        return new Adapter<AK>(k);
    }

    public void clear() {
        this.backingMap.clear();
    }

    public boolean containsKey(Object arg0) {
        return this.backingMap.containsKey(w(arg0));
    }

    public boolean containsValue(Object value) {
        return this.backingMap.containsValue(value);
    }

    public Set<Map.Entry<K, V>> entrySet() {
        return new FilterSet<Map.Entry<Adapter<K>, V>, Map.Entry<K,V>>(
                this.backingMap.entrySet(),
                new Filter<Map.Entry<Adapter<K>, V>, Map.Entry<K,V>>() {
                    public Map.Entry<Adapter<K>, V> from(final Map.Entry<K, V> to) {
                        return new Map.Entry<Adapter<K>, V>() {
                            public Adapter<K> getKey() {
                                return new Adapter<K>(to.getKey());
                            }
                            public V getValue() {
                                return to.getValue();
                            }
                            public V setValue(V value) {
                                return to.setValue(value);
                            }                            
                        };
                    }

                    public Map.Entry<K, V> to(final Map.Entry<Adapter<K>, V> from) {
                        return new Map.Entry<K, V>() {
                            public K getKey() {
                                return from.getKey().object;
                            }
                            public V getValue() {
                                return from.getValue();
                            }
                            public V setValue(V value) {
                                return from.setValue(value);
                            }                            
                        };                    
                    }
                });
    }

    public V get(Object key) {
        return this.backingMap.get(w(key));
    }

    public boolean isEmpty() {
        return this.backingMap.isEmpty();
    }

    public Set<K> keySet() {
        return new FilterSet<Adapter<K>, K>(
                this.backingMap.keySet(),
                new Filter<Adapter<K>, K>() {
                    public Adapter<K> from(K to) {
                        return new Adapter<K>(to);
                    }
                    public K to(Adapter<K> from) {
                        return from.object;
                    }                    
                });
    }

    public V put(K key, V value) {
        return this.backingMap.put(w(key), value);
    }

    public void putAll(Map<? extends K, ? extends V> t) {
        for (Map.Entry<? extends K, ? extends V> entry : t.entrySet()) {
            this.put(entry.getKey(), entry.getValue());
        }
    }

    public V remove(Object key) {
        return this.backingMap.remove(w(key));
    }

    public int size() {
        return this.backingMap.size();
    }

    public Collection<V> values() {
        return this.backingMap.values();
    }

}
