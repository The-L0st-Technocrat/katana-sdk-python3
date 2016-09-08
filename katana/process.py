import asyncio
import logging
import signal

from multiprocessing import Process

import zmq.asyncio

from .utils import install_uvevent_loop

LOG = logging.getLogger(__name__)


class ComponentProcess(Process):
    """Component child process class.

    Each process initializes an event loop to run a given number
    of worker tasks.

    Each worker task is used to asynchronically handle service
    discovery commands.

    """

    def __init__(self, channel, workers, callback, cli_args, *args, **kwargs):
        """Constructor.

        :param channel: IPC channel to connect to parent process.
        :type channel: str.
        :param workers: Number of component workers to start.
        :type workers: int.
        :param callback: A callable to use a request handler callback.
        :type callback: callable.
        :param cli_args: Command line arguments used to run current process.
        :type cli_args: dict.

        """

        super().__init__(*args, **kwargs)
        self.__stop = False
        self.tasks = []
        self.sleep_period = 0.1
        self.loop = None
        self.channel = channel
        self.workers = workers
        self.callback = callback
        self.cli_args = cli_args

    @property
    def worker_factory(self):
        """Worker class or factory.

        When factory is a callable it must return a
        `ComponentWorker` instance.

        :rtype: `ComponentWorker` or callable.

        """

        raise NotImplementedError()

    def create_worker_task(self):
        """Create a new worker task to process incoming requests.

        After worker is created it is added to the event loop as a task.

        :rtype: `Task`

        """

        worker = self.worker_factory(
            self.callback,
            self.channel,
            self.cli_args,
            )
        task = self.loop.create_task(worker())
        self.tasks.append(task)
        return task

    def restart_worker_task(self, task):
        """Remove a worker task and start a new one.

        Task is restarted only when is done.

        :param task: Task to be restarted.
        :type task: `Task`

        """

        # Task must be done before it is restarted
        if not task.done():
            LOG.error(
                'Failed to restart unfinished task in SDK PID: "%s"',
                self.pid,
                )
            return

        LOG.debug('Restarting task in SDK PID: "%s"', self.pid)
        self.tasks.remove(task)
        self.create_worker_task()

    def handle_task_exception(self, task, exc):
        """Handler for tasks that finished because of an error.

        By default exceptions are raised.

        :param task: Task to handle.
        :rtype task: `Task`
        :param exc: Exception raised inside the task.
        :rtype exc: `Exception`

        """

        try:
            raise exc
        except:
            LOG.exception('Task error in SDK PID: "%s"', self.pid)

        self.restart_worker_task(task)

    def handle_task_done(self, task):
        """Handler for tasks that are finished.

        These tasks didn't raise an exception, they were finished
        naturally of because `CancelledError` was raised.

        :param task: Task to handle.
        :rtype task: `Task`

        """

    def handle_main_task_done(self, task):
        """Callback called when main task is finished.

        :param task: Main task.
        :type task: `Task`

        """

        self.loop.stop()

    @asyncio.coroutine
    def run_tasks(self):
        """Run manager until halt is called.

        Runs an infinite loop that checks status for all tasks
        and then sleeps for a short period.

        """

        while 1:
            yield from asyncio.sleep(self.sleep_period)

            # Check tasks status
            for task in self.tasks:
                # Skip when task is not done
                if not task.done():
                    continue

                # When task is finished check for errors
                exc = task.exception()
                if exc:
                    self.handle_task_exception(task, exc)
                else:
                    self.handle_task_done(task)

            if self.__stop:
                yield from self.stop_tasks()
                break

    @asyncio.coroutine
    def stop_tasks(self, timeout=1.5):
        """Stop all tasks.

        :param timeout: Seconds to wait for all tasks to be finished.
        :param timeout: float

        """

        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to finish
        yield from asyncio.wait(self.tasks, timeout=timeout)

    def run(self):
        """Child process main code."""

        # Ignore CTRL-C (parent process terminates children using SIGTERM)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Create an event loop for current process
        install_uvevent_loop()
        self.loop = zmq.asyncio.ZMQEventLoop()
        asyncio.set_event_loop(self.loop)

        # Create a task for each worker
        for number in range(self.workers):
            self.create_worker_task()

        # Gracefully terminate process on SIGTERM events.
        self.loop.add_signal_handler(signal.SIGTERM, self.stop)

        # Create a main task and run it until SIGTERM is received
        task = self.loop.create_task(self.run_tasks())
        task.add_done_callback(self.handle_main_task_done)
        self.loop.run_forever()

    def stop(self, *args, **kwargs):
        """Stop main loop and all running tasks."""

        LOG.debug('Terminating all tasks in SDK PID: "%s"', self.pid)
        self.__stop = True