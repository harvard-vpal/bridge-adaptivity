# flake8: noqa: F405
from .base import *  # noqa: F401,F403
import requests


def get_ec2_task_ip():
    """
    Retrieve the internal ip address(es) for task, if running with AWS EC2
    Used to get ips to add to ALLOWED_HOSTS setting, for load balancer health checks.
    Based on https://gist.github.com/dryan/8271687
    """
    EC2_PRIVATE_IP = None
    try:
        EC2_PRIVATE_IP = requests.get('http://169.254.169.254/latest/meta-data/local-ipv4', timeout=0.01).text
    except requests.exceptions.RequestException:
        pass

    return EC2_PRIVATE_IP


def get_ecs_task_ips():
    """
    Retrieve the internal ip address(es) for task, if running with AWS ECS and awsvpc networking mode
    Used to get ips to add to ALLOWED_HOSTS setting, for load balancer health checks
    See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint.html
    Uses V2 endpoint: http://169.254.170.2/v2/metadata (v3 not yet available on fargate)
    :return: list of internal ip addresses
    """
    ip_addresses = []
    r = requests.get("http://169.254.170.2/v2/metadata", timeout=0.01)
    if r.ok:
        task_metadata = r.json()
        for container in task_metadata['Containers']:
            for network in container['Networks']:
                if network['NetworkMode'] == 'awsvpc':
                    ip_addresses.extend(network['IPv4Addresses'])
    return ip_addresses


# Add internal IPs to ALLOWED_HOSTS in order to support load balancer health checks 
ec2_task_ip = get_ec2_task_ip()
if ec2_task_ip():
    ALLOWED_HOSTS.append(ec2_task_ip)

ecs_task_ips = get_ecs_task_ips()
if ecs_task_ips:
    ALLOWED_HOSTS.extend(ecs_task_ips)
