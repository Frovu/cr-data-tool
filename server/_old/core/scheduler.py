from concurrent.futures import ThreadPoolExecutor
from threading import Timer
import time

class Task:
    def __init__(self, executor, func, args=(), name='calculating', progress=False):
        self.name = name
        self.progress = progress
        if progress:
            self.prog = [0, 0, '', False]
            args = (self.prog,) + args
        self.future = executor.submit(func, *args)

    def failed(self):
        return self.progress and self.prog[3]

    def result(self):
        return self.future.result()

    def done(self):
        return self.future.done()

    def get_name(self):
        return (self.progress and self.prog[2]) or self.name

    def get_progress(self):
        return self.prog[0] / (self.prog[1] or 1) if self.progress else None

class Query:
    def __init__(self, executor, tasks=[]):
        self.executor = executor
        self.done = False
        self.failed = False
        self.tasks = []
        self.submit_tasks(tasks)

    def append_tasks(self, tasks):
        self.tasks += tasks

    def submit_tasks(self, tasks):
        for task in tasks:
            self.tasks.append(Task(self.executor, *task))

    def is_failed(self):
        return self.failed

    def status(self):
        if not self.done and not self.failed:
            self.prog = prog = dict()
            for task in self.tasks:
                if ff := task.failed():
                    self.done = False
                    self.failed = {'failed': ff}
                    return self.done, self.failed
                t_prog = 1 if task.done() else task.get_progress() or 0
                name = task.get_name()
                if not prog.get(name):
                    prog[name] = [t_prog, 1]
                else:
                    prog[name][0] += t_prog
                    prog[name][1] += 1
            for name in prog:
                prog[name] = round(prog[name][0] / prog[name][1], 2)
            self.done = True
            for task in self.tasks:
                if not task.done():
                    self.done = False
        return self.done, self.failed or {'progress': self.prog}

    def result(self):
        return [t.result() for t in self.tasks] if self.done else None

    def await_result(self):
        return [t.result() for t in self.tasks]

class Scheduler:
    def __init__(self, workers=4, ttl=60):
        self.ttl = ttl
        self.queries = dict()
        self.cache = dict()
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def get(self, key):
        return self.queries.get(key)

    def _dispose(self, key):
        del self.cache[key]

    def status(self, key):
        chached = self.cache.get(key)
        query = chached or self.get(key)
        done, info = query.status() if query else (None, None)
        if (done or (query and query.is_failed())) and not chached:
            del self.queries[key]
            if self.ttl:
                self.cache[key] = query
                timer = Timer(self.ttl, self._dispose, key)
        return done, query.result() if done else info

    def query_tasks(self, key, tasks):
        return self.query(key, Query(self.executor, tasks))

    def query(self, key, q):
        if self.get(key) is not None:
            del self.queries[key]
            if key in self.cache:
                del self.cache[key]
        self.queries[key] = q
        return self.queries[key]

    # NOTE: wrapping like this does not allow for completed tasks which did not produce persistent result
    def wrap(self, argc: int=1):
        def decorator(func):
            def wrapper(*args, **kwargs):
                is_done, info = self.status(args[:argc])
                if is_done == False:
                    return 'failed' if info.get('failed') else 'busy', info
                result, error, tasks = func(*args, **kwargs)
                if result:
                    return 'ok', result
                if error:
                    return 'failed', error
                assert tasks
                return 'accepted', self.query_tasks(args[:argc], tasks)
            return wrapper
        return decorator
