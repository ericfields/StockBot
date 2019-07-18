from multiprocessing.pool import ThreadPool

class thread_pool():
    def __init__(self, num_threads):
        self.pool = Pool(num_threads)

    def __enter__(self):
        return self.pool

    def __exit__(self, type, value, traceback):
        self.pool.close()

class Pool():
    def __init__(self, num_threads):
        self.pool = ThreadPool(processes=num_threads)

    def call(self, method, *args, **kwargs):
        return self.pool.apply_async(method, tuple(args), kwargs)

    def close(self):
        self.pool.close()
