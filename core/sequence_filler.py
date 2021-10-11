from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import traceback
import logging

def subtract(ints, interval, period):
    res = []
    for i in ints:
        if interval[0] <= i[0]:
            if interval[1] >= i[1]:
                continue
            elif interval[1] >= i[0]:
                res.append((interval[1]+period, i[1]))
        elif interval[0] <= i[1]:
            res.append((i[0], interval[0]-period))
            if interval[1] < i[1]:
                res.append((interval[1]+period, i[1]))
        else:
            res.append(i)
    return res

class Scheduler:
    def __init__(self):
        self.cache = dict()
        self.alias = dict()
        self.info = dict()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def get_info(self, token, t_from, t_to):
        pass

    def get(self, token, t_from, t_to):
        alias = self.alias.get((token, t_from, t_to))
        key = alias or (token, t_from, t_to)
        entry = self.cache.get(key)
        done = entry and sum([f.done() for f in entry]) == len(entry)
        if done:
            del self.cache[key]
            for al in self.alias:
                if self.alias[al] == key:
                    del self.alias[al]
        return done, self.info.get(key) if entry else None

    def schedule(self, token, t_from, t_to, period, tasks):
        intervals = [(t_from, t_to)]
        for key in self.cache:
            intervals = subtract(intervals, key[1:], period)
            if not intervals:
                self.alias[(token, t_from, t_to)] = key
                return
        self.info[(token, t_from, t_to)] = dict()
        for task in tasks:
            self.info[(token, t_from, t_to)][task[0]]
            args = (, i[0], i[1], period, )
            fs = [self.executor.submit(fill_fn, *+args)) for i in intervals]
            self.cache[(token, t_from, t_to)] = fs


    def fill_fn(self, t_from, t_to, period, info_id, integrity_fn, process_fn, multiproc=False, page_size=4096):
        try:
            missing = integrity_fn(t_from, t_to, period)
            if multiproc and len(missing) > 1:
                executor = ProcessPoolExecutor(max_workers=4)
            for interval in missing:
                batch = period*page_size
                for i_start in range(interval[0], interval[1], batch):
                    i_end = i_start+batch if i_start+batch < interval[1] else interval[1]
                    if multiproc:
                        executor.submit(process_fn, i_start, i_end)
                    else:
                        process_fn(i_start, i_end)
            if multiproc:
                executor.shutdown()
        except Exception:
                logging.error(f'Failed seq fill_fn: {traceback.format_exc()}')
