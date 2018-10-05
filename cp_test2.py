import tarfile
import time
from tempfile import TemporaryFile

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

import tarfile
import os
from os import listdir
from os.path import isfile, join
import base64

if __name__ == "__main__":
    config.load_kube_config()
    c = Configuration()
    c.assert_hostname = False
    Configuration.set_default(c)
    api = core_v1_api.CoreV1Api()
    name = 'nginx-deploymentmonblog-6cc4595cb7-k2m7t'

    onlyfiles = [f for f in listdir("/tmp/monblog/") if isfile(join("/tmp/monblog/", f))]

    with tarfile.open("/tmp/monblog.tgz", "w:gz") as tar:
        for name in onlyfiles:
            tar.add("/tmp/monblog/"+name)
        #tar.add(source_dir, arcname=os.path.basename(source_dir))

    with open("/tmp/monblog.tgz", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        #print(encoded_string)

    b64str = encoded_string.decode()

    exec_command = [
        '/bin/sh',
        '-c',
        'echo '+b64str,
        ' | base64 --decode > /tmp/test.tgz'
    ]
    #exec_command = ['ls']
    resp = stream(api.connect_get_namespaced_pod_exec, name, 'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=False, _preload_content=False)
    print("Response: " + resp)

def cpfile():

    exec_command = ['sh']
    resp = stream(api.connect_get_namespaced_pod_exec, name, 'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=False,
                  _preload_content=False)

    source_file = '/tmp/dash'
    destination_file = '/usr/share/nginx/html/index.html'
    file = open(source_file, "r")

    commands = []
    commands.append("cat <<'EOF' >" + destination_file + "\n")
    commands.append(file.read())
    commands.append("EOF\n")

    while resp.is_open():
        resp.update(timeout=1)
        if resp.peek_stdout():
            print("STDOUT: %s" % resp.read_stdout())
        if resp.peek_stderr():
            print("STDERR: %s" % resp.read_stderr())

        if commands:
            c = commands.pop(0)
            resp.write_stdin(c)
        else:
            break

    resp.close()
