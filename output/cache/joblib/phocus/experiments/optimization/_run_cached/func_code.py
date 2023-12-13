# first line: 30
@memory.cache
def _run_cached(experiment):
    return plan_route(experiment.params)
