from django.core.cache import cache
import hashlib

class Cache():
    def set(key, value):
        cache.set(Cache.__cache_key(key), value)

    def get(key):
        return cache.get(Cache.__cache_key(key))

    def __cache_key(key_str):
        m = hashlib.md5()
        m.update(str.encode(key_str))
        return m.hexdigest()
