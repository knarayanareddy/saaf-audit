import os
import subprocess


def lookup_user(handle):
    out = subprocess.run(f"gh api /users/{handle} --jq .id", shell=True, capture_output=True, text=True)
    return out.stdout


def convert(name):
    cmd = "pandoc {} -o out.pdf".format(name)
    os.system(cmd)


def archive(folder):
    subprocess.check_output("tar czf backup.tgz " + folder, shell=True)


def wrap(path):
    subprocess.Popen(["bash", "-c", f"cat {path} | wc -l"])


def listing(d):
    return os.popen("ls -la %s" % d).read()
