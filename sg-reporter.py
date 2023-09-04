import boto3
from botocore.exceptions import ClientError
import requests
import os
import git
import shutil
import csv
import pandas as pd

client = boto3.client("sts")
account_id = client.get_caller_identity()["Account"]
# By passing account_id to avoid publishing it on gitlab
account_id = 1111111111111

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
results_egress=[]
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
                        "security_group-as-source",
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
    for egress_statement in sec_groups_p[sec_group]["egress"]:
        protocol=egress_statement['IpProtocol']
        if protocol == '-1':
            ports_opened = "any"
            protocol = "ip"
        elif egress_statement['FromPort']==egress_statement['ToPort']:
            ports_opened = egress_statement['FromPort']
        else:
            ports_opened = str(egress_statement['FromPort']) + "-" + str(egress_statement['ToPort'])
        if len(egress_statement["IpRanges"]) == 0:
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
                results_egress.append(
                    [
                        account_id,
                        sec_id,
                        item[0],
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        "security_group-as-destination",
                        src_string[1:],
                        item[5]
                    ]
                )                            
        for ip_range in egress_statement['IpRanges']:
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
                        results_egress.append(
                            [
                                account_id,
                                sec_id,
                                ec2_instance,
                                ec2_id,
                                ec2_ip_addr,
                                dst_subnet,
                                f"R-{role_dst}-{site_dst}",
                                subnet,
                                f"R-{role}-{site}",
                                f"{protocol}={ports_opened}"
                            ]
                        )


headers_inbound =        [
            "Account ID",
            "Security Group",
            "Source subnet",
            "Source role-site",
            "Ec2 name",
            "Ec2 Id",
            "Ec2 IP",
            "Destination subnet",
            "Destination role-site",  
            "port and protocol"         
        ]

headers_outbound =         [
            "Account ID",
            "Security Group",
            "Ec2 name",
            "Ec2 Id",
            "Ec2 IP",
            "Source subnet",
            "Source role-site",
            "Destination subnet",
            "Destination role-site",  
            "port and protocol"         
        ]

#Creating sorted panda df
df_inbound = pd.DataFrame(results, columns=headers_inbound)
df_sorted_inbound = df_inbound.sort_values(by = ['Security Group', 'Ec2 Id', 'Source subnet'], ascending = [True, True, True], na_position = 'first')
df_outbound = pd.DataFrame(results_egress, columns=headers_outbound)
df_sorted_outbound = df_outbound.sort_values(by = ['Security Group', 'Ec2 Id', 'Destination subnet'], ascending = [True, True, True], na_position = 'first')


# Clone a remote repository
repo_url = "git@github.com:guidodg86/sg-database.git"
local_path = "./temp_sg-database/"
repo = git.Repo.clone_from(repo_url, local_path)
origin = repo.remote(name='origin')

df_sorted_inbound.to_csv(local_path + 'inbound.csv', index=False)
df_sorted_outbound.to_csv(local_path + 'outbound.csv', index=False)


repo.index.add(['inbound.csv', 'outbound.csv'])
repo.index.commit('Automatic update of sg information')
origin.push()

shutil.rmtree(local_path, ignore_errors=True)
pass



