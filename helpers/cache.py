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
    def delete(cls, key):
        return caches[cls.cache_name()].delete(Cache.__cache_key(key))

    @classmethod
    def cache_name(cls):
        # Get the default cache
        return 'default'

    def __cache_key(key_str):
        # Cache key must be shorter than than 250 characters
        # and cannot have any whitespace or control characters
        if len(key_str) >= 250 or (' ' in key_str) or ("\\" in key_str):
            m = hashlib.md5()
            m.update(str.encode(key_str))
            key_str = m.hexdigest()
        return key_str
