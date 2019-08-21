from django.core.cache import caches
import hashlib

class Cache():
    @classmethod
    def set(cls, key, value, timeout=None):
        caches[cls.cache_name()].set(Cache.__cache_key(key), value, timeout)

    @classmethod
    def get(cls, key):
        return caches[cls.cache_name()].get(Cache.__cache_key(key))

    @classmethod
    def cache_name(cls):
        # Get the default cache
        return 'default'

    def __cache_key(key_str):
        m = hashlib.md5()
        m.update(str.encode(key_str))
        return m.hexdigest()
