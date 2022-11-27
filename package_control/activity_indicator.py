import sublime
from threading import Lock


class ActivityIndicator:
    """
    An animated text-based indicator to show that some activity is in progress.

    The `target` argument should be a :class:`sublime.View` or :class:`sublime.Window`.
    The indicator will be shown in the status bar of that view or window.
    If `label` is provided, then it will be shown next to the animation.

    :class:`ActivityIndicator` can be used as a context manager.
    """

    def __init__(self, label=None):
        self.label = label
        self.interval = 120
        self._lock = Lock()
        self._running = False
        self._ticks = 0
        self._view = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def clear(self):
        if self._view:
            self._view.erase_status('_package_control')
            self._view = None

    def start(self):
        """
        Start displaying the indicator and animate it.

        :raise RuntimeError: if the indicator is already running.
        """

        with self._lock:
            if self._running:
                raise RuntimeError('Timer is already running')
            self._running = True
            self._ticks = 0
            self.update(self.render_indicator_text())
            sublime.set_timeout(self.tick, self.interval)

    def stop(self):
        """
        Stop displaying the indicator.

        If the indicator is not running, do nothing.
        """

        with self._lock:
            if self._running:
                self._running = False
                self.clear()

    def finish(self, message):
        """
        Stop the indicator and display a final status message

        :param message:
            The final status message to display
        """

        with self._lock:
            if self._running:
                self._running = False
                self.update(message)

                def clear():
                    with self._lock:
                        self.clear()

                sublime.set_timeout(clear, 2000)

    def tick(self):
        """
        Invoke status bar update with specified interval.
        """

        with self._lock:
            if self._running:
                self._ticks += 1
                self.update(self.render_indicator_text())
                sublime.set_timeout(self.tick, self.interval)

    def update(self, text):
        """
        Update activity indicator and label in status bar.

        :param text:
            The text to display in the status bar
        """

        view = sublime.active_window().active_view()
        if view and view != self._view:
            if self._view:
                self._view.erase_status('_package_control')
            self._view = view
        if self._view:
            self._view.set_status('_package_control', text)

    def render_indicator_text(self):
        """
        Render activity indicator and label.

        :returns:
            The activity indicator string to display in the status bar
        """

        text = '⣷⣯⣟⡿⢿⣻⣽⣾'[self._ticks % 8]
        if self.label:
            text += " " + self.label
        return text

    def set_label(self, label):
        with self._lock:
            self.label = label
