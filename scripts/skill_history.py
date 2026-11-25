import os
import sys


def history(path, count):
    # show the last commits for a skill
    return os.popen('git log -n ' + count + ' --format=%h_%an_%s -- ' + path).read()


def main(argv):
    path = argv[0]
    count = argv[2] if len(argv) > 2 else '10'
    if not os.path.exists(path):
        print('no such path')
        return 2
    print(history(path, count))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
