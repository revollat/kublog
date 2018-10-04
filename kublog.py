from kubernetes import client, config, watch
from kubernetes.client.apis import core_v1_api
from kubernetes.stream import stream
import os
import hashlib

# from kubernetes.client.rest import ApiException
# from pprint import pprint

DOMAIN = "revollat.net"
DEPLOYMENT_NAME = "nginx-deployment"


def process(crds, obj, operation, metadata, name):
    namespace = metadata.get("namespace")
    content = obj["spec"]["content"]
    hash_object = hashlib.sha256(content.encode('utf-8'))
    hex_dig = hash_object.hexdigest()

    api_instance = client.CoreV1Api()
    extensions_v1beta1 = client.ExtensionsV1beta1Api()
    deployment = create_deployment_object(name)

    service = client.V1Service()
    service.api_version = "v1"
    service.kind = "Service"
    service.metadata = client.V1ObjectMeta(name="my-service-" + name)
    svcspec = client.V1ServiceSpec()
    svcspec.selector = {"app": "nginx" + name}
    svcspec.ports = [client.V1ServicePort(protocol="TCP", port=80, target_port=9376)]
    service.spec = svcspec

    if operation == "ADDED":

        create_deployment(extensions_v1beta1, deployment)

        api_instance.create_namespaced_service(namespace="default", body=service)

        obj["spec"]["contenthash"] = hex_dig
        crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "kublogs", name, obj)

    elif operation == "MODIFIED":

        contenthash = obj["spec"]["contenthash"]

        if hex_dig == contenthash:
            print("Pas de changement ...")
        else:
            print("Une modif a eu lieu ...")
            obj["spec"]["contenthash"] = hex_dig
            crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "kublogs", name, obj)

            ret = api_instance.list_namespaced_pod(namespace="default", label_selector="app=nginx"+name)
            podname = ret.items[0].metadata.name

            print("DEBUG : podname = " + podname)

            exec_command = ['sh']

            api = core_v1_api.CoreV1Api()

            resp = stream(api.connect_get_namespaced_pod_exec, podname, 'default', command=exec_command,
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

    elif operation == "DELETED":

        delete_deployment(extensions_v1beta1, name)
        api_instance.delete_namespaced_service(name="my-service-"+name, namespace="default", body=service)


def create_deployment_object(deployname):
    # Configureate Pod template container
    container = client.V1Container(
        name="nginx",
        image="nginx:1.7.9",
        ports=[client.V1ContainerPort(container_port=80)])
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "nginx"+deployname}),
        spec=client.V1PodSpec(containers=[container]))
    # Create the specification of deployment
    spec = client.ExtensionsV1beta1DeploymentSpec(
        replicas=1,
        template=template)
    # Instantiate the deployment object
    deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME+deployname),
        spec=spec)

    return deployment


def create_deployment(api_instance, deployment):
    # Create deployement
    api_response = api_instance.create_namespaced_deployment(
        body=deployment,
        namespace="default")
    print("Deployment created. status='%s'" % str(api_response.status))


def delete_deployment(api_instance, name):
    # Delete deployment
    api_response = api_instance.delete_namespaced_deployment(
        name=DEPLOYMENT_NAME+name,
        namespace="default",
        body=client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=5))
    print("Deployment deleted. status='%s'" % str(api_response.status))


if __name__ == "__main__":
    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()

    configuration = client.Configuration()
    configuration.assert_hostname = False
    api_client = client.api_client.ApiClient(configuration=configuration)
    crds = client.CustomObjectsApi(api_client)

    # try:
    #     api_instance = client.CoreV1Api()
    #     api_response = api_instance.list_namespaced_pod(namespace="default", watch=False)
    #     pprint(api_response)
    # except ApiException as e:
    #   print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)

    # # --------------------------------
    # exec_command = ['sh']
    # api = core_v1_api.CoreV1Api()
    #
    # resp = stream(api.connect_get_namespaced_pod_exec, "nginx-deploymentmonblog-6cc4595cb7-kdhvk",
    #               'default', command=exec_command, stderr=True, stdin=True, stdout=True, tty=False, _preload_content=False)
    #
    # source_file = '/tmp/thetest'
    # destination_file = '/usr/share/nginx/html/index.html'
    # file = open(source_file, "r")
    # commands = list()
    # commands.append("cat <<'EOF' >" + destination_file + "\n")
    # commands.append(file.read())
    # commands.append("EOF\n")
    #
    # while resp.is_open():
    #     resp.update(timeout=1)
    #     if resp.peek_stdout():
    #         print("STDOUT: %s" % resp.read_stdout())
    #     if resp.peek_stderr():
    #         print("STDERR: %s" % resp.read_stderr())
    #     if commands:
    #         c = commands.pop(0)
    #         resp.write_stdin(c)
    #     else:
    #         break
    #
    # resp.close()
    #
    # exit(0)
    # # --------------------------------

    print("Watch for kublogs ...")
    resource_version = ''
    while True:
        stream = watch.Watch().stream(crds.list_cluster_custom_object, DOMAIN, "v1", "kublogs",
                                      resource_version=resource_version)
        for event in stream:
            obj = event["object"]
            operation = event['type']
            spec = obj.get("spec")
            if not spec:
                continue
            metadata = obj.get("metadata")
            resource_version = metadata['resourceVersion']
            name = metadata['name']
            print("Handling %s on %s" % (operation, name))
            process(crds, obj, operation, metadata, name)
