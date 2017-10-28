import re


class ProtocolResult:
    ok_init_str = 'E0:Ok'

    def __init__(self, response_line, data=None):
        match = re.match('^E([0-9]):', response_line)
        if not match:
            raise ValueError('Invalid response line: %s' % response_line)

        self.ordinal = int(match[1])
        self.message = response_line.split(':')[1]
        self.data = data

    @staticmethod
    def is_valid_result(response_line):
        return re.match('^E([0-9]):', response_line)

    def __bool__(self):
        return self.ordinal == 0

    def __str__(self):
        str = '%s (Code: %d)' % (self.message, self.ordinal)
        if self.data:
            str += ' (Data: %s)' % self.data
        return str
