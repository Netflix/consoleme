import signal


class Timeout(object):
    def __init__(self, seconds: int = 1, error_message: str = "Timeout") -> None:
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self) -> None:
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type: None, value: None, traceback: None) -> None:
        signal.alarm(0)
