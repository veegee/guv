"""Logger configuration module

This looks nicest on a terminal configured with "solarized" colours.
"""
import logging
import sys

configured = False


class ColouredFormatter(logging.Formatter):
    RESET = '\x1B[0m'  # INFO
    RED = '\x1B[31m'  # ERROR, CRITICAL, FATAL
    GREEN = '\x1B[32m'  # INFO
    YELLOW = '\x1B[33m'  # WARNING
    BLUE = '\x1B[34m'  # INFO
    MAGENTA = '\x1B[35m'  # INFO
    CYAN = '\x1B[36m'  # INFO
    WHITE = '\x1B[37m'  # INFO
    BRGREEN = '\x1B[01;32m'  # DEBUG (grey in solarized for terminals)

    def format(self, record, colour=False):
        message = super().format(record)

        if not colour:
            return message

        level_no = record.levelno
        if level_no >= logging.CRITICAL:
            colour = self.RED
        elif level_no >= logging.ERROR:
            colour = self.RED
        elif level_no >= logging.WARNING:
            colour = self.YELLOW
        elif level_no >= 29:
            colour = self.MAGENTA
        elif level_no >= 28:
            colour = self.CYAN
        elif level_no >= 27:
            colour = self.GREEN
        elif level_no >= 26:
            colour = self.BLUE
        elif level_no >= 25:
            colour = self.WHITE
        elif level_no >= logging.INFO:
            colour = self.RESET
        elif level_no >= logging.DEBUG:
            colour = self.BRGREEN
        else:
            colour = self.RESET

        message = colour + message + self.RESET

        return message


class ColouredHandler(logging.StreamHandler):
    def __init__(self, stream=sys.stdout):
        super().__init__(stream)

    def format(self, record, colour=False):
        if not isinstance(self.formatter, ColouredFormatter):
            self.formatter = ColouredFormatter()

        return self.formatter.format(record, colour)

    def emit(self, record):
        stream = self.stream
        try:
            if hasattr(sys, 'called_from_test') and sys.called_from_test:
                msg = self.format(record, True)
            else:
                msg = self.format(record, stream.isatty())
            stream.write(msg)
            stream.write(self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def configure():
    if configured:
        return

    logging.addLevelName(25, 'INFO')
    logging.addLevelName(26, 'INFO')
    logging.addLevelName(27, 'INFO')
    logging.addLevelName(28, 'INFO')
    logging.addLevelName(29, 'INFO')

    h = ColouredHandler()
    h.formatter = ColouredFormatter('{asctime} {name:8} {levelname:8} {message}',
                                    '%Y-%m-%d %H:%M:%S', '{')
    if sys.version_info >= (3, 3):
        logging.basicConfig(level=logging.DEBUG, handlers=[h])
    else:
        # Python 3.2 doesn't support the `handlers` parameter for `logging.basicConfig()`
        logging.basicConfig(level=logging.DEBUG)
        logging.root.handlers[0] = h

    logging.getLogger('requests').setLevel(logging.WARNING)


configure()
