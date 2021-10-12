from concurrent.futures import ThreadPoolExecutor

class Task:
    def __init__(self, executor, func, args=(), name='calculating', progress=False):
        self.name = name
        self.progress = progress
        if progress:
            self.prog = [0, 0, '']
            args = (self.prog,) + args
        self.future = executor.submit(func, *args)

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
        self.tasks = []
        self.submit_tasks(tasks)

    def append_tasks(self, tasks):
        self.tasks += tasks

    def submit_tasks(self, tasks):
        for task in tasks:
            self.tasks.append(Task(self.executor, *task))

    def status(self):
        if not self.done:
            self.prog = prog = dict()
            for task in self.tasks:
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
        return self.done, self.prog

    def result(self):
        return [t.result() for t in self.tasks] if self.done else None

class Scheduler:
    def __init__(self, workers=4):
        self.queries = dict()
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def get(self, key):
        return self.queries.get(key)

    def status(self, key):
        query = self.get(key)
        done, info = query.status() if query else (None, None)
        if done:
            info = query.result()
            del self.queries[key]
        return done, info

    def query_tasks(self, key, tasks):
        return self.query(key, Query(self.executor, tasks))

    def query(self, key, q):
        if self.get(key) is not None:
            return None
        self.queries[key] = q
        return self.queries[key]
