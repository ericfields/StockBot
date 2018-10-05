from multiprocessing.pool import ThreadPool
from queue import Queue

def async_call(method, *args, **kwargs):
    pool = ThreadPool(processes=1)
    async_result = pool.apply_async(method, tuple(args), kwargs)
    return async_result
