import boto3
from botocore.exceptions import ClientError
import requests
import os


client = boto3.client("sts")
account_id = client.get_caller_identity()["Account"]

ec2 = boto3.client('ec2')


try:
    sec_group_data = ec2.describe_security_groups()
except ClientError as e:
    print(e)

try:
    ec2_instances = ec2.describe_instances()
except ClientError as e:
    print(e)

sec_groups_p = {}
for item in sec_group_data['SecurityGroups']:
    name = item['GroupName']
    if "default" in name:
        continue
    group_id = item['GroupId']
    ingress = item['IpPermissions']
    egress = item['IpPermissionsEgress']
    sec_groups_p[name] = {}
    sec_groups_p[name]['id'] = group_id
    sec_groups_p[name]['ingress'] = ingress
    sec_groups_p[name]['egress'] = egress

ec2_p = {}     
for item in ec2_instances['Reservations']:
    for ec2 in item['Instances']:
        id = ec2['InstanceId']
        ip_addr = ec2['PrivateIpAddress']
        name = ec2['Tags'][0]['Value']
        sgs_applied = ec2['SecurityGroups']
        ec2_p[name]={}
        ec2_p[name]['id']=id
        ec2_p[name]['ip_addr']=ip_addr
        ec2_p[name]['sgs_applied']=sgs_applied     
pass


headers_netbox = {
    'Authorization': f'Token {os.getenv("TF_VAR_netbox_token")}',
}
prefix_url = "http://127.0.0.1:8000/api/ipam/prefixes/?q="
prefix_ip_addr = "http://127.0.0.1:8000/api/ipam/prefixes/?contains="


results=[]
for sec_group in sec_groups_p:
    sec_id = sec_groups_p[sec_group]["id"]
    for ingress_statement in sec_groups_p[sec_group]["ingress"]:
        protocol=ingress_statement['IpProtocol']
        if ingress_statement['FromPort']==ingress_statement['ToPort']:
            ports_opened = ingress_statement['FromPort']
        else:
            ports_opened = str(ingress_statement['FromPort']) + "-" + str(ingress_statement['ToPort'])
        if len(ingress_statement["IpRanges"]) == 0:
            draft_results = []
            for ec2_instance in ec2_p:
                for item in ec2_p[ec2_instance]['sgs_applied']:
                    if item['GroupId'] == sec_id:
                        ec2_ip_addr = ec2_p[ec2_instance]['ip_addr']
                        ec2_id = ec2_p[ec2_instance]['id']
                        target_url = prefix_ip_addr + ec2_ip_addr 
                        ip_data =  requests.get(target_url , headers=headers_netbox).json()
                        dst_subnet = ip_data['results'][0]['prefix']
                        site_dst = ip_data['results'][0]['site']['name']
                        role_dst = ip_data['results'][0]['role']['name']
                        draft_results.append(
                            [
                                ec2_instance,
                                ec2_id,
                                ec2_ip_addr,
                                dst_subnet,
                                f"R-{role_dst}-{site_dst}",
                                f"{protocol}={ports_opened}"
                            ]
                        )
                        ec2_source_list = {}
                        for item in draft_results:
                            ec2_source_list[item[1]] = item[0]
                        for item in draft_results:
                            src_string = ""
                            for instance in ec2_source_list:
                                if instance == item[1]:
                                    continue
                                src_string = src_string + ";" + ec2_source_list[instance] + "__" + instance
                            results.append(
                                [
                                    account_id,
                                    sec_id,
                                    "security_group as source",
                                    src_string[1:],
                                    item[0],
                                    item[1],
                                    item[2],
                                    item[3],
                                    item[4],
                                    item[5]
                                ]
                            )                            
        for ip_range in ingress_statement['IpRanges']:
            subnet = ip_range['CidrIp']
            if subnet == "0.0.0.0/0":
                site = "sa"
                role = "any"
            else:
                target_url = prefix_url + subnet
                prefix_data =  requests.get(target_url , headers=headers_netbox).json()
                site = prefix_data['results'][0]['site']['name']
                role = prefix_data['results'][0]['role']['name']
            for ec2_instance in ec2_p:
                for item in ec2_p[ec2_instance]['sgs_applied']:
                    if item['GroupId'] == sec_id:
                        ec2_ip_addr = ec2_p[ec2_instance]['ip_addr']
                        ec2_id = ec2_p[ec2_instance]['id']
                        target_url = prefix_ip_addr + ec2_ip_addr 
                        ip_data =  requests.get(target_url , headers=headers_netbox).json()
                        dst_subnet = ip_data['results'][0]['prefix']
                        site_dst = ip_data['results'][0]['site']['name']
                        role_dst = ip_data['results'][0]['role']['name']
                        results.append(
                            [
                                account_id,
                                sec_id,
                                subnet,
                                f"R-{role}-{site}",
                                ec2_instance,
                                ec2_id,
                                ec2_ip_addr,
                                dst_subnet,
                                f"R-{role_dst}-{site_dst}",
                                f"{protocol}={ports_opened}"
                            ]
                        )
        
pass


