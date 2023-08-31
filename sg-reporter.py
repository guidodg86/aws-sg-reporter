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

pass