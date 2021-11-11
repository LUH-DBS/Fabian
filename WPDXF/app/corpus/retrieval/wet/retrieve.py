import logging
import logging.handlers
import multiprocessing as mp
import random
from glob import glob
from os import path
from typing import Callable, List, Optional

from corpus.retrieval.wet.consume import main_subroutine
from corpus.retrieval.wet.produce import retrieve
from utils.settings import Settings
from utils.utils import make_dirs

TERMINATE = "\0"

"""
Terminology:
archive_name: The archive's filename without any path specification.
archive_part: The archive's partial location as it is in the 'wet.paths' file.
archive_path: The archive's absolute filepath (usually ...data/corpus/wet/<archive_name>)
"""


def main_routine(limit: int = None, mp_method: str = "spawn", **kwargs):
    """Main routine for corpus retrieval. 
       Initializes and manages workers, loads and distributes input values.

    Args:
        limit (int, optional): The maximal amount of files retrieved and processed. 
            If less are present, the limit must not be reached. Defaults to None.

        mp_method (str, optional): Start method for multiprocessing workers. 
            If set to None, the routine will be executed as a single-threaded process.
            Used for testing, not relevant otherwise. Defaults to "spawn".
    """
    settings = Settings()

    if mp_method is not None:
        NUM_PRODUCER = settings.NUM_PRODUCER
        NUM_CONSUMER = settings.NUM_CONSUMER
        mp.set_start_method(mp_method)

        manager = mp.Manager()
        # queue_in: 'wet.paths' -> retrieve (produce)
        queue_in = manager.Queue(NUM_PRODUCER)
        # queue_pipe: retrieve -> main_subroutine (consume)
        queue_pipe = manager.Queue()

        downloaded = set()
        # Use this if some files were preloaded.
        downloaded = set(glob(settings.WET_FILES + "*.gz"))

        processed = set()
        processed = set(glob(settings.TERM_STORE + "*.gz"))

        for p in downloaded:
            queue_pipe.put(path.basename(p))

        producer = start_processes(NUM_PRODUCER, "P{}", retrieve, queue_in, queue_pipe)
        consumer = start_processes(NUM_CONSUMER, "C{}", main_subroutine, queue_pipe)

        # Put new elements into queue_in until there are no further tasks to start.
        for task in sample_tasks(limit=limit, given_vals=downloaded | processed):
            queue_in.put(task)

        # Join and finish
        [queue_in.put(TERMINATE) for _ in range(NUM_PRODUCER)]
        [p.join() for p in producer]
        [queue_pipe.put(TERMINATE) for _ in range(NUM_CONSUMER)]
        [p.join() for p in consumer]

    else:
        for task in sample_tasks(limit=limit):
            out = retrieve(task)
            main_subroutine(out)


def start_processes(
    num_producer: int,
    id_str: str,
    func: Callable[[mp.Queue, Optional[mp.Queue]], None],
    queue_in: mp.Queue,
    queue_out: mp.Queue = None,
) -> List[mp.Process]:
    """Generic process spawner. Creates, configures and starts multiple processes as specified.

    Args:
        num_producer (int): Total amount of processes to be returned.
        id_str (str): Format string to identify each worker. Format string will be filled by this method
        func (Callable[[mp.Queue, Optional[mp.Queue]], None]): Function takes values from an input queue, 
            manipulates them and passes the result to an output queue (if given). 
            Will be executed by each Process.
        queue_in (mp.Queue): Multithreaded input queue, distributes workload between processes. 
            Used as input queue for each process.
        queue_out (mp.Queue, optional): Multithreaded output queue, collects workload of all processes.

    Returns:
        List[mp.Process]: A list of started Processes
    """
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


def process(
    id: str,
    func: Callable[[mp.Queue, Optional[mp.Queue]], None],
    queue_in: mp.Queue,
    queue_out: mp.Queue = None,
    **kwargs,
):
    """Generic multiprocess function wrapper. 
    Handles all multithreading related actions to keep workflows seperated.
    Configures individual log files (as logging is not thread-safe by default).
    Waits for new items from queue_in until a termination symbol appears.

    Args:
        id (str): Worker's id
        func (Callable[[mp.Queue, Optional[mp.Queue]], None]): Function to be executed by the worker.
        queue_in (mp.Queue): Input queue, which distributes workload.
        queue_out (mp.Queue, optional): [description]. Output queue, which collects workload. Defaults to None.
    """
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
    """Worker logging configuration: 
    Each worker gets its own handler to avoid simultaneous writing from multiple workers.

    Args:
        id (str): Worker's id, used to identify the log file.
    """
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
    """Collects and samples values from 'wet.paths' file. 
    If a limit is present, <limit> values are randomly sampled from 'wet.paths'.
    If given_vals is present, this set is considered as given/truth. 
    These values will not be part of the set returned by the method.

    Args:
        limit (int, optional): The maximum of values returned. If less values exist, the limit must not be reached. Defaults to None.
        given_vals (set, optional): A set of values that must be excluded from sampling. 
            given_vals and 'wet.paths' are assumed to be sets of archive_name or archive_part values. 
            They are compared and excluded based on their os.path.basename. Defaults to None.

    Returns:
        set: A set of unique archive_parts.
    """

    with open(Settings().WET_PATHS) as file:
        sample_from = set(file.read().split())

    if given_vals is not None:
        given_vals = set(map(path.basename, given_vals))
        sample_from = set(
            filter(lambda x: path.basename(x) not in given_vals, sample_from)
        )
        if limit is not None:
            limit -= len(given_vals)
    if limit is not None:
        return random.sample(sample_from, max(limit, 0))
    return sample_from
