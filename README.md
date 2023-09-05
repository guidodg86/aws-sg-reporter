# aws-sg-reporter
Documents security groups in AWS with info from netbox

## Requeriments
```
boto3==1.28.38
botocore==1.31.38
certifi==2023.7.22
charset-normalizer==3.2.0
gitdb==4.0.10
GitPython==3.1.34
idna==3.4
jmespath==1.0.1
numpy==1.24.4
pandas==2.0.3
python-dateutil==2.8.2
pytz==2023.3
requests==2.31.0
s3transfer==0.6.2
six==1.16.0
smmap==5.0.0
tzdata==2023.3
urllib3==1.26.16
```

## Env variables
You will need to use `aws configure` to set up connection with AWS. Also a variable named `TF_VAR_netbox_token` needs to be initialized to connect to local netbox instance

## Usage
In order to use the script we need set up a netbox locally and have a AWS account. To populate netbox and configure AWS you can use [aws-sample-infra](https://github.com/guidodg86/aws-sample-infra)

## Results
Reports will update two csv files located in [aws-sample-infra] (https://github.com/guidodg86/sg-database/)