import timeit

from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.db.queryGenerator_old import QueryExecutorOld
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.utils import load_and_prepare_examples

file = (
    "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/n_14_k_3_5.json"
)
example_split = 0.2
examples, queries, queries_gt = load_and_prepare_examples(file, example_split)
examples = [Example(i, *example) for i, example in enumerate(examples)]
queries = [Query(i + len(examples), query) for i, query in enumerate(queries)]


q0 = QueryExecutorOld()
q0_res = q0.get_uris_for(examples, queries)

q1 = QueryExecutor()
q1_res = q1.get_uris_for(examples, queries)

assert q0_res == q1_res

print("Q0", timeit.timeit(lambda: q0.get_uris_for(examples, queries), number=10))
print("Q1", timeit.timeit(lambda: q1.get_uris_for(examples, queries), number=10))
