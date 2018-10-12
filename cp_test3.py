import tarfile
import time
import os
import base64
from tempfile import TemporaryFile

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

from os import listdir
from os.path import isfile, join

if 'KUBERNETES_PORT' in os.environ:
	config.load_incluster_config()
else:
	config.load_kube_config()

c = Configuration()
c.assert_hostname = False
Configuration.set_default(c)
api = core_v1_api.CoreV1Api()
name = 'nginx-deploymentmonblog-6cc4595cb7-k2m7t'
resp = None

# try:
#     resp = api.read_namespaced_pod(name=name, namespace='default')
# except ApiException as e:
#     if e.status != 404:
#         print("Unknown error: %s" % e)
#         exit(1)

# Create Tar
kublogname = "monblog"
onlyfiles = [f for f in listdir("/tmp/"+kublogname+"/") if isfile(join("/tmp/"+kublogname+"/", f))]
with tarfile.open("/tmp/"+kublogname+".tar", "w") as tar:
    for fname in onlyfiles:
        tar.add("/tmp/"+kublogname+"/"+fname)
# END Create Tar

# Copying file
exec_command = ['tar', 'xvf', '-', '-C', '/']
resp = stream(api.connect_get_namespaced_pod_exec, name, 'default',
              command=exec_command,
              stderr=True, stdin=True,
              stdout=True, tty=False,
              _preload_content=False)

source_file = '/tmp/'+kublogname+'.tar'
destination_file = '/tmp/alors'
file = open(source_file, "rb")
buffer = b''
with open(source_file, "rb") as file:
    buffer += file.read()

commands = []
commands.append(buffer)

while resp.is_open():
    resp.update(timeout=1)
    if resp.peek_stdout():
        print("STDOUT: %s" % resp.read_stdout())
    if resp.peek_stderr():
        print("STDERR: %s" % resp.read_stderr())
    if commands:
        c = commands.pop(0)
        print("Running command...\n")
        resp.write_stdin(c.decode())
    else:
        break
resp.close()
