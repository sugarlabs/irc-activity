import os
urkpath = os.path.dirname(__file__)


def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath


def pprint(obj, depth=-2):
    depth += 2

    string = []

    if isinstance(obj, dict):
        if obj:
            string.append('{\n')

            for key in obj:
                string.append('%s%s%s' % (' ' * depth, repr(key), ': '))
                string += pprint(obj[key], depth)

            string.append('%s%s' % (' ' * depth, '},\n'))

        else:
            string.append('{},\n')

    elif isinstance(obj, list):
        if obj:
            string.append('[\n')

            for item in obj:
                string.append('%s' % (' ' * depth))
                string += pprint(item, depth)

            string.append('%s%s' % (' ' * depth, '],\n'))

        else:
            string.append('[],\n')

    else:
        string.append('%s,\n' % (repr(obj),))

    if depth:
        return string
    else:
        return ''.join(string)[:-2]


def save(*args):
    pass

#events.register('Exit', 'post', save)

conf = {}

if __name__ == '__main__':
    print(pprint(conf))
