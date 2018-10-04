import tarfile
import time
from tempfile import TemporaryFile

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

config.load_kube_config()
c = Configuration()
c.assert_hostname = False
Configuration.set_default(c)
api = core_v1_api.CoreV1Api()
name = 'nginx-deploymentmonblog-6cc4595cb7-llqv5'

# resp = None
# try:
#     resp = api.read_namespaced_pod(name=name,
#                                    namespace='default')
# except ApiException as e:
#     if e.status != 404:
#         print("Unknown error: %s" % e)
#         exit(1)
#
# if not resp:
#     print("Pod %s does not exits. Creating it..." % name)
#     pod_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'Pod',
#         'metadata': {
#             'name': name
#         },
#         'spec': {
#             'containers': [{
#                 'image': 'busybox',
#                 'name': 'sleep',
#                 "args": [
#                     "/bin/sh",
#                     "-c",
#                     "while true;do date;sleep 5; done"
#                 ]
#             }]
#         }
#     }
#     resp = api.create_namespaced_pod(body=pod_manifest,
#                                      namespace='default')
#     while True:
#         resp = api.read_namespaced_pod(name=name,
#                                        namespace='default')
#         if resp.status.phase != 'Pending':
#             break
#         time.sleep(1)
#     print("Done.")

# Calling exec interactively.

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
