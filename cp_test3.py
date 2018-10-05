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

if 'KUBERNETES_PORT' in os.environ:
	config.load_incluster_config()
else:
	config.load_kube_config()

c = Configuration()
c.assert_hostname = False
Configuration.set_default(c)
api = core_v1_api.CoreV1Api()
name = 'nginx-deploymentmonblog-6cc4595cb7-8kvbq'

resp = None
try:
    resp = api.read_namespaced_pod(name=name, namespace='default')
except ApiException as e:
    if e.status != 404:
        print("Unknown error: %s" % e)
        exit(1)

# Copying file
exec_command = ['tar', 'xvf', '-', '-C', '/']
resp = stream(api.connect_get_namespaced_pod_exec, name, 'default',
              command=exec_command,
              stderr=True, stdin=True,
              stdout=True, tty=False,
              _preload_content=False)

source_file = '/tmp/dash.tar'
destination_file = '/tmp/sh'

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
        #print("Running command... %s\n" % c)
        resp.write_stdin(c)
    else:
        break
resp.close()