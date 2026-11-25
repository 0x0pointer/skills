import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def history(path, count):
    out = subprocess.run(['git', 'log', '-n', str(count), '--format=%h %an %s', '--', path], cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout


def main(argv):
    if not argv:
        sys.stderr.write('usage: skill_history.py PATH [-n COUNT]' + chr(10))
        return 2
    path = os.path.abspath(argv[0])
    count = 10
    if len(argv) == 3 and argv[1] == '-n' and argv[2].isdigit():
        count = int(argv[2])
    elif len(argv) != 1:
        sys.stderr.write('usage: skill_history.py PATH [-n COUNT]' + chr(10))
        return 2
    inside = os.path.commonpath([ROOT, path]) == ROOT
    if count < 1 or not inside or not os.path.exists(path):
        sys.stderr.write('not a path in this repository: ' + argv[0] + chr(10))
        return 2
    sys.stdout.write(history(path, count))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
