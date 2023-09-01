import boto3
from botocore.exceptions import ClientError

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