import logging
import logging.handlers
import multiprocessing as mp
import random
from glob import glob
from os import path

from corpus.retrieval.wet.consume import main_subroutine
from corpus.retrieval.wet.produce import retrieve
from settings import Settings
from utils import make_dirs

TERMINATE = "\0"


def main_routine(limit: int = None, mp_method: str = "spawn", **kwargs):
    settings = Settings()

    if mp_method is not None:
        NUM_PRODUCER = settings.NUM_PRODUCER
        NUM_CONSUMER = settings.NUM_CONSUMER
        mp.set_start_method(mp_method)

        manager = mp.Manager()
        queue_in = manager.Queue(NUM_PRODUCER)
        queue_pipe = manager.Queue()

        downloaded = set()

        # Use this if some files were preloaded.
        downloaded = set(glob(settings.WET_FILES + "*.gz"))
        for p in downloaded:
            queue_pipe.put(path.basename(p))

        producer = start_processes(NUM_PRODUCER, "P{}", retrieve, queue_in, queue_pipe)
        consumer = start_processes(NUM_CONSUMER, "C{}", main_subroutine, queue_pipe)

        for task in sample_tasks(limit=limit, given_vals=downloaded):
            queue_in.put(task)

        [queue_in.put(TERMINATE) for _ in range(NUM_PRODUCER)]
        [p.join() for p in producer]
        [queue_pipe.put(TERMINATE) for _ in range(NUM_CONSUMER)]
        [p.join() for p in consumer]

    else:
        for task in sample_tasks(limit=limit):
            main_subroutine(task)


def start_processes(
    num_producer: int,
    id_str: str,
    func,
    queue_in: mp.Queue,
    queue_out: mp.Queue = None,
):
    out = []
    for i in range(num_producer):
        p = mp.Process(
            target=process,
            kwargs={
                "id": id_str.format(i),
                "queue_in": queue_in,
                "queue_out": queue_out,
                "func": func,
            },
        )
        p.start()
        out.append(p)
    return out


def process(id: str, func, queue_in: mp.Queue, queue_out: mp.Queue = None, **kwargs):
    configure_worker(id)
    while True:
        item = queue_in.get()
        if item == TERMINATE:
            logging.info("Termination symbol received.")
            return
        item = func(item, **kwargs)
        if queue_out is not None:
            queue_out.put(item)


def configure_worker(id: str):
    log_file = path.join(Settings().LOG_PATH, f"worker-{id}.log")
    make_dirs(log_file)
    h = logging.FileHandler(log_file)
    h.setFormatter(
        logging.Formatter("%(asctime)s %(processName)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.DEBUG)


def sample_tasks(limit: int = None, given_vals: set = None) -> set:
    limit = limit or 0
    with open(Settings().WET_PATHS) as file:
        sample_from = set(file.read().split())

    if given_vals is not None:
        given_vals = set(map(path.basename, given_vals))
        sample_from = set(
            filter(lambda x: path.basename(x) not in given_vals, sample_from)
        )
        if limit > 0:
            limit -= len(given_vals)
    if limit > 0:
        return random.sample(sample_from, limit)
    if limit < 0:
        return set()
    return sample_from
