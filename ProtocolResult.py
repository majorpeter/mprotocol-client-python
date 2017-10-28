import re


class ProtocolResult:
    def __init__(self, response_line):
        match = re.match('^E([0-9]):', response_line)
        if not match:
            raise ValueError('Invalid response line: %s' % response_line)

        self.ordinal = int(match[1])
        self.message = response_line.split(':')[1]
        self.data = None

    @staticmethod
    def is_valid_result(response_line):
        return re.match('^E([0-9]):', response_line)

    def __bool__(self):
        return self.ordinal == 0

    def __str__(self):
        return '%s (Code: %d)' % (self.message, self.ordinal)