from kubernetes import client, config, watch
from kubernetes.client.apis import core_v1_api
from kubernetes.stream import stream
import os
import hashlib

# from kubernetes.client.rest import ApiException
# from pprint import pprint

DOMAIN = "revollat.net"
DEPLOYMENT_NAME = "nginx-deployment"

name = "monblog"

if 'KUBERNETES_PORT' in os.environ:
    config.load_incluster_config()
else:
    config.load_kube_config()

configuration = client.Configuration()

api_instance = client.CoreV1Api()

ret = api_instance.list_namespaced_pod(namespace="default", label_selector="app=nginx" + name)
podname = ret.items[0].metadata.name

print("DEBUG : podname = " + podname)

# Transfert de fichiers
# =========================================================================
exec_command = ['sh']

# apidl = core_v1_api.CoreV1Api()

resp = stream(api_instance.connect_get_namespaced_pod_exec, podname, 'default', command=exec_command,
              stderr=True, stdin=True, stdout=True, tty=False, _preload_content=False)

source_file = '/tmp/thetest'
destination_file = '/usr/share/nginx/html/index.html'
file = open(source_file, "r")
commands = list()
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
