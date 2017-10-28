import re


class ProtocolResult:
    ok_init_str = 'E0:Ok'

    def __init__(self, response_line, data=None):
        match = re.match('^E([0-9]):', response_line)
        if match:
            self.ordinal = int(match[1])
            self.message = response_line.split(':')[1]
            self.data = data
        elif response_line.startswith('P_'):
            self.ordinal = 0
            self.message = 'Ok'

            self.data = {
                'type': response_line[2:response_line.index(' ')],
                'value': response_line[response_line.index('=')+1:]
            }
        else:
            raise ValueError('Invalid response line: %s' % response_line)

    @staticmethod
    def is_valid_result(response_line):
        if re.match('^E([0-9]):', response_line):
            return True
        if response_line.startswith('P_'):
            return True
        return False

    def __bool__(self):
        return self.ordinal == 0

    def __str__(self):
        str = '%s (Code: %d)' % (self.message, self.ordinal)
        if self.data:
            str += ' (Data: %s)' % self.data
        return str
