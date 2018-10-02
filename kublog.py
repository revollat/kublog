from kubernetes import client, config, watch
import os
import hashlib

DOMAIN = "revollat.net"
DEPLOYMENT_NAME = "nginx-deployment"

def process(crds, obj, operation):

    metadata = obj.get("metadata")
    name = metadata.get("name")
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
    spec = client.V1ServiceSpec()
    spec.selector = {"app": "nginx" + name}
    spec.ports = [client.V1ServicePort(protocol="TCP", port=80, target_port=9376)]
    service.spec = spec

    if operation == "ADDED":
        create_deployment(extensions_v1beta1, deployment)


        api_instance.create_namespaced_service(namespace="default", body=service)


        obj["spec"]["contenthash"] = hex_dig
        crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "kublogs", name, obj)

    elif operation == "MODIFIED":
        contenthash = obj["spec"]["contenthash"]

        if hex_dig == contenthash :
            print("Pas de changement ...")
        else:
            print("Une modif a eu lieu ...")
            obj["spec"]["contenthash"] = hex_dig
            crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "kublogs", name, obj)


    elif operation == "DELETED":
        delete_deployment(extensions_v1beta1, name)

        api_instance.delete_namespaced_service(name="my-service-"+name, namespace="default", body=service)



def create_deployment_object(name):
    # Configureate Pod template container
    container = client.V1Container(
        name="nginx",
        image="nginx:1.7.9",
        ports=[client.V1ContainerPort(container_port=80)])
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "nginx"+name}),
        spec=client.V1PodSpec(containers=[container]))
    # Create the specification of deployment
    spec = client.ExtensionsV1beta1DeploymentSpec(
        replicas=1,
        template=template)
    # Instantiate the deployment object
    deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME+name),
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

    print("Watch for kublogs ...")
    resource_version = ''
    while True:
        stream = watch.Watch().stream(crds.list_cluster_custom_object, DOMAIN, "v1", "kublogs", resource_version=resource_version)
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
            process(crds, obj, operation)
