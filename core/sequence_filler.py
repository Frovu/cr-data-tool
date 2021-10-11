from concurrent.futures import ThreadPoolExecutor, wait

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
        self.executor = ThreadPoolExecutor(max_workers=4)

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
        return done

    def schedule(self, token, t_from, t_to, period, func, args=()):
        intervals = [(t_from, t_to)]
        for key in self.cache:
            intervals = subtract(intervals, key[1:], period)
            if not intervals:
                self.alias[(token, t_from, t_to)] = key
                return
        self.cache[(token, t_from, t_to)] = [
            self.executor.submit(func, *((t_from, t_to)+args)) for i in intervals ]
