import asyncio

import pytest

from procrastinate import exceptions, job_context, worker


@pytest.fixture
def test_worker(app):
    return worker.Worker(app=app, queues=["yay"])


@pytest.fixture
def context():
    return job_context.JobContext()


def test_worker_load_task_known_missing(test_worker, context):
    test_worker.known_missing_tasks.add("foobarbaz")
    with pytest.raises(exceptions.TaskNotFound):
        test_worker.load_task("foobarbaz", context=context)


def test_worker_load_task_known_task(app, test_worker, context):
    @app.task
    def task_func():
        pass

    assert (
        test_worker.load_task("tests.unit.test_worker_sync.task_func", context=context)
        == task_func
    )


def test_worker_load_task_new_missing(test_worker, context):

    with pytest.raises(exceptions.TaskNotFound):
        test_worker.load_task("foobarbaz", context=context)

    assert test_worker.known_missing_tasks == {"foobarbaz"}


unknown_task = None


def test_worker_load_task_unknown_task(app, caplog, context):
    global unknown_task
    test_worker = worker.Worker(app=app, queues=["yay"])

    @app.task
    def task_func():
        pass

    unknown_task = task_func

    assert (
        test_worker.load_task(
            "tests.unit.test_worker_sync.unknown_task", context=context
        )
        == task_func
    )

    assert [record for record in caplog.records if record.action == "load_dynamic_task"]


def test_stop(test_worker, caplog):
    caplog.set_level("INFO")
    test_worker.notify_event = asyncio.Event()

    test_worker.stop()

    assert test_worker.stop_requested is True
    assert test_worker.notify_event.is_set()
    assert caplog.messages == ["Stop requested, no job currently running"]


def test_stop_log_job(test_worker, caplog, context, job_factory):
    caplog.set_level("INFO")
    test_worker.notify_event = asyncio.Event()
    job = job_factory()
    context = context.evolve(job=job)
    test_worker.current_context = context

    test_worker.stop()

    assert test_worker.stop_requested is True
    assert test_worker.notify_event.is_set()
    assert caplog.messages == ["Stop requested, waiting for job to finish: bla()"]
