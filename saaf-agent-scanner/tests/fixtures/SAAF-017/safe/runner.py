import os
import shlex
import subprocess


def lookup_user(handle):
    if not handle.replace("-", "").isalnum():
        raise ValueError("bad handle")
    out = subprocess.run(["gh", "api", f"/users/{handle}", "--jq", ".id"], capture_output=True, text=True)
    return out.stdout


def convert(name):
    subprocess.run(["pandoc", "--", name, "-o", "out.pdf"], check=True)


def archive(folder):
    subprocess.check_output("tar czf backup.tgz " + shlex.quote(folder), shell=True)


def wrap(path):
    subprocess.Popen(["bash", "-c", 'cat "$1" | wc -l', "_", path])


def fixed():
    return os.popen("ls -la /var/log").read()


def with_const():
    subprocess.run(f"echo {os.getpid()}", shell=False)
    subprocess.run("git status", shell=True)
