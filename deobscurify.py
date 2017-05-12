import re


DECL_PATTERN = re.compile(r'var \w+ = ([\[])')
END_PATTERN = re.compile(r'([\]];)')
FULL_DECL_PATTERN = re.compile(r'var (\w+) = \[(.*)\];\n')


class ContextManager():
    def __init__(self):
        self.__vars = [dict()]
        self.__keys = set()
        self.__depth = 0

    def get(self, key, index=None, depth=None):
        '''
        Get the value in the lowest depth that has more than index values.
        Keeps going up checking, until exhaustion.
        '''
        for i in range((depth or self.__depth), 0, -1):
            vars = self.__vars[i]
            if key in vars:
                if index is None:
                    return vars[key]
                elif len(vars[key]) > index:
                    return vars[key][index]

    def __setitem__(self, key, value):
        self.add_var(key, value)

    def __iter__(self):
        for k in self.__vars[self.__depth].keys():
            yield k

    def keys(self, depth=None):
        return self.__keys

    def add_var(self, key, values, depth=None):
        self.__vars[depth or self.__depth][key] = values
        self.__keys.add(key)

    def check_depth(self, line):
        '''
        Calculates if the current depth has to
        increase or decrease.
        '''

        opening = line.find('{') > -1
        closing = line.find('}') > -1
        if line.find('* @') > -1:
            pass
        elif opening:
            self.__depth += 1
            if len(self.__vars) <= self.__depth:
                self.__vars.extend(dict() for _ in range(self.__depth))
        elif closing:
            self.__depth -= 1

    def replacer(context, match):
        '''
        Replace the call to an array position with it's value.
        '''
        var, index = match.group(1), match.group(2)
        ret = context.get(var, int(index))
        return ret

    def fix_values(context, values, name):
        '''
        The regex I made to split the array values isn't perfect,
        so it needs some cleaning.
        For example, blank elements and sometimes one is split
        in pieces.
        '''

        if values is None:
            return []

        values = list(filter(lambda x: len(x) > 0, values))

        i = 0
        while i < len(values):
            check = values[i][0] in '"(' and values[i][-1] not in '")'
            check |= values[i][0] not in '"(' and values[i][-1] in '")'
            # check &= values[i].count('+') > 1 or values[i].count(')') > 1
            if check:
                values[i] += values[i + 1]
                values.remove(values[i + 1])
                i -= 1
            i += 1

        return values

    def extract_variable(context, lines, current, threshold=4):
        '''
        Check if there is an javascript array declaration in this line.
        Keeps going until gets the full declaration and save into the dict.
        Only stores arrays with length higher than `threshold`.
        '''
        has_var = re.search(DECL_PATTERN, lines[current])
        context.check_depth(lines[current])
        if has_var:
            kind = has_var.group(1)
            var = ''
            if kind == '[':
                while re.search(END_PATTERN, lines[current]) is None:
                    var += lines[current].strip('\n')
                    # removes the variable declaration
                    lines[current] = ''
                    current += 1
                var += lines[current]
                # removes the variable declaration
                lines[current] = ''
                context.check_depth(lines[current])

            name, value = re.search(FULL_DECL_PATTERN, var).groups()
            values = re.split('("\w+", )?(,\s+)(?!",)', value)[0::3]
            values = context.fix_values(values, name)
            if len(values) > threshold:
                context[name] = values

        return current + 1

    def remove_multiline_comments(context, lines):
        '''
        As the name says, it removes the multiline comments.
        '''
        started = False
        for line in lines:
            if '/*' in line:
                started = True

            if not started:
                yield line

            if '*/' in line:
                started = False

    def concat_strings(context, lines):
        def simple_concat(line):
            # "b" + "ter"
            return re.sub(
                r'"([^"]*)" \+ "([^"]*)"',
                lambda x: '"' + x.group(1) + x.group(2) + '"',
                line
            )

        def simple_parentheses(line):
            # + ("ob")
            # ("ob") +
            print(line)
            line = re.sub(
                r'\+ \("([^"]*)"\)',
                lambda x: '+ "' + x.group(1) + '"',
                line
            )
            line = re.sub(
                r'\("([^"]*)"\) \+',
                lambda x: '"' + x.group(1) + '" +',
                line
            )
            print(line)
            return line

        def master_concat(line):
            stop = False
            while not stop:
                if '" + "' in line:
                    line = simple_concat(line)
                elif '+ ("' in line or '") +' in line:
                    line = simple_parentheses(line)
                else:
                    stop = True
            return line

        for line in lines:
            line = master_concat(line)
            yield line

    def proccess_file(context, file_in, file_out):
        with open(file_in, 'r') as inp:
            lines = inp.readlines()

            lines = list(context.remove_multiline_comments(lines))

            current = 0
            while current < len(lines):
                print('{line_number}:{depth}::{line_text}'.format(
                    line_number=current,
                    depth=context._ContextManager__depth,
                    line_text=lines[current].strip('\n'),
                ))
                current = context.extract_variable(lines, current)

                if current < len(lines):
                    for var in sorted(context.keys(), key=lambda k: len(k), reverse=True):
                        if re.search(r'(' + re.escape(var) + r')\[(\d+)\]', lines[current]):
                            lines[current] = re.sub(
                                r'(' + re.escape(var) + r')\[(\d+)\]',
                                context.replacer, lines[current]
                            )
            lines = list(context.concat_strings(lines))

        with open(file_out, 'w+') as out:
            out.write(''.join(lines))


if __name__ == '__main__':
    cm = ContextManager()
    cm.proccess_file(
        file_in='./response2.js',
        file_out='./response2.1.js'
    )
    del cm
