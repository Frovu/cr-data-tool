from concurrent.futures import ThreadPoolExecutor
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

    def subtract_from(self, intervals, period):
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
        super().__init__()

    def merge_query(self, token, t_from, t_to, q):
        sq = self.get((token, t_from, t_to))
        return sq and sq.append_tasks(q.tasks)

    def do_fill(self, token, t_from, t_to, period, tasks):
        key = (token, t_from, t_to)
        q = self.query(key, IntervalQuery(self.executor, t_from, t_to))
        if not q: return
        intervals = [(t_from, t_to)]
        for kk in self.queries.keys():
            if kk[0] != token or key == kk: continue
            cq = self.get(kk)
            intervals, dep = cq.subtract_from(intervals, period)
            if dep:
                q.append_tasks(cq.tasks)
            if not intervals:
                return
        for task in tasks:
            for i in intervals:
                fargs = (i[0], i[1], period) + (task[2] or ())
                targs = (task[1], fargs, task[0], True)
                q.submit_tasks([targs])

def fill_fn(prog, t_from, t_to, period, integrity_fn, process_fn, multiproc=False, workers=4, page_size=3600):
    try:
        missing = integrity_fn((t_from, t_to))
        exec = ThreadPoolExecutor(max_workers=workers) if multiproc else None
        for interval in missing:
            batch = period*page_size
            for i_start in range(interval[0], interval[1], batch):
                i_end = i_start+batch if i_start+batch < interval[1] else interval[1]
                prog[1] += i_end - i_start
                def proc(ist, ien):
                    try:
                        process_fn((ist, ien))
                    except Exception as e:
                        logging.error(f'Failed seq process_fn: {traceback.format_exc()}')
                    prog[0] += ien - ist
                if exec:
                    exec.submit(proc, i_start, i_end)
                else:
                    proc(i_start, i_end)
        if exec:
            exec.shutdown(wait=True)
    except Exception:
            logging.error(f'Failed seq fill_fn: {traceback.format_exc()}')
