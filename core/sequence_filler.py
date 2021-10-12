from concurrent.futures import ProcessPoolExecutor
from core.scheduler import Scheduler, Query
import traceback
import logging

# TODO: dependency check is performed only by query edges
# performing per-task check may improve performance.
# tho it will be useless overcomlication with expected amount of users
class IntervalQuery(Query):
    def __init__(self, executor, i_start, i_end):
        super().__init__(executor)
        self.t_from = i_start
        self.t_to = i_end

    def subtract_from(intervals, period):
        res = []
        for i in intervals:
            if self.t_from <= i[0]:
                if self.t_to >= i[1]:
                    continue
                elif self.t_to >= i[0]:
                    res.append((self.t_to+period, i[1]))
            elif self.t_from <= i[1]:
                res.append((i[0], self.t_from-period))
                if self.t_to < i[1]:
                    res.append((self.t_to+period, i[1]))
            else:
                res.append(i)
        return res, int != res

class SequenceFiller(Scheduler):
    def __init__(self):
        super().__init__(query_cl=IntervalQuery)

    def do_fill(self, token, t_from, t_to, period, tasks):
        key = (token, t_from, t_to)
        q = self.query(key, IntervalQuery(self.executor, t_from, t_to))
        if not q: return
        intervals = [(t_from, t_to)]
        for key in self.queries.keys():
            if key[0] != token: continue
            cq = self.get(key)
            intervals, dep = cq.subtract_from(intervals, period)
            if dep:
                q.append_tasks(cq.tasks)
            if not intervals:
                return
        for task in tasks:
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
