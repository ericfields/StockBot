from multiprocessing.pool import ThreadPool

class Pool():
    def __init__(self, num_threads):
        self.pool = ThreadPool(processes=num_threads)

    def call(self, method, *args, **kwargs):
        return self.pool.apply_async(method, tuple(args), kwargs)
