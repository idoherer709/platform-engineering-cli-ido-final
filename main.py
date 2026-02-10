import click
import boto3
import sys
import os
import time
from botocore.exceptions import ClientError

# קבועים (Constants)
TAG_NAME = 'CreatedBy'
TAG_VALUE = 'platform-cli'

def get_latest_ami():
    """Helper function to get the latest Amazon Linux 2 AMI ID."""
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(
        Name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2',
        WithDecryption=False
    )
    return response['Parameter']['Value']

@click.group()
def cli():
    """Platform Engineering CLI tool for managing AWS resources."""
    pass

# --- EC2 Group ---
@cli.group()
def ec2():
    """Manage EC2 instances."""
    pass

@ec2.command()
@click.option('--owner', required=True, help='Name of the owner')
@click.option('--project', required=True, help='Project name')
@click.option('--env', type=click.Choice(['dev', 'test', 'prod']), required=True, help='Environment')
@click.option('--type', 'instance_type', type=click.Choice(['t2.micro', 't3.micro']), default='t2.micro', help='Instance type')
def create(owner, project, env, instance_type):
    """Create a new EC2 instance."""
    ec2_resource = boto3.resource('ec2')
    
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': f'tag:{TAG_NAME}', 'Values': [TAG_VALUE]}]
    )
    active_instances = [i for i in instances if i.state['Name'] != 'terminated']
    
    if len(active_instances) >= 2:
        click.echo("Error: Cannot create more than 2 instances via CLI (Hard Cap Reached).")
        return

    click.echo("Fetching latest Amazon Linux 2 AMI...")
    try:
        ami_id = get_latest_ami()
    except Exception as e:
        click.echo(f"Error fetching AMI: {e}")
        return

    click.echo(f"Creating EC2 instance ({instance_type}) for {owner} in {env}...")

    try:
        new_instances = ec2_resource.create_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': TAG_NAME, 'Value': TAG_VALUE},
                        {'Key': 'Owner', 'Value': owner},
                        {'Key': 'Project', 'Value': project},
                        {'Key': 'Environment', 'Value': env},
                        {'Key': 'Name', 'Value': f"{project}-{env}-server"}
                    ]
                }
            ]
        )
        instance = new_instances[0]
        click.echo("Waiting for instance to start running...")
        instance.wait_until_running() 
        instance.reload() 
        click.echo(f"Success! Instance created.")
        click.echo(f"ID: {instance.id}")
        click.echo(f"State: {instance.state['Name']}")
        click.echo(f"Public IP: {instance.public_ip_address}")
    except Exception as e:
        click.echo(f"Error creating instance: {e}")

@ec2.command()
def list():
    """List CLI-created instances."""
    ec2_resource = boto3.resource('ec2')
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': f'tag:{TAG_NAME}', 'Values': [TAG_VALUE]}]
    )
    click.echo(f"Listing instances with tag {TAG_NAME}={TAG_VALUE}...")
    count = 0
    for instance in instances:
        if instance.state['Name'] == 'terminated':
            continue
        click.echo(f"- ID: {instance.id}, Type: {instance.instance_type}, State: {instance.state['Name']}")
        tags_dict = {tag['Key']: tag['Value'] for tag in instance.tags} if instance.tags else {}
        click.echo(f"  Tags: Owner={tags_dict.get('Owner')}, Env={tags_dict.get('Environment')}")
        count += 1
    if count == 0:
        click.echo("No active instances found.")

@ec2.command()
@click.argument('instance_id')
def stop(instance_id):
    """Stop an EC2 instance."""
    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)
    try:
        instance.load()
        tags = {t['Key']: t['Value'] for t in instance.tags or []}
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Instance {instance_id} not managed by CLI.")
            sys.exit(1)
        click.echo(f"Stopping {instance_id}...")
        instance.stop()
        instance.wait_until_stopped()
        click.echo("Stopped.")
    except Exception as e:
        click.echo(f"Error: {e}")

@ec2.command()
@click.argument('instance_id')
def start(instance_id):
    """Start an EC2 instance."""
    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)
    try:
        instance.load()
        tags = {t['Key']: t['Value'] for t in instance.tags or []}
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Instance {instance_id} not managed by CLI.")
            sys.exit(1)
        click.echo(f"Starting {instance_id}...")
        instance.start()
        instance.wait_until_running()
        click.echo("Running.")
    except Exception as e:
        click.echo(f"Error: {e}")


# --- S3 Group ---
@cli.group()
def s3():
    """Manage S3 buckets."""
    pass

@s3.command()
def list():
    """List CLI-created buckets."""
    s3_resource = boto3.resource('s3')
    
    click.echo(f"Listing buckets with tag {TAG_NAME}={TAG_VALUE}...")
    
    found_any = False
    for bucket in s3_resource.buckets.all():
        try:
            tag_set = bucket.Tagging().tag_set
            tags = {t['Key']: t['Value'] for t in tag_set}
            
            if tags.get(TAG_NAME) == TAG_VALUE:
                click.echo(f"- Name: {bucket.name}")
                click.echo(f"  Tags: Owner={tags.get('Owner')}, Env={tags.get('Environment')}")
                found_any = True
                
        except ClientError:
            continue
            
    if not found_any:
        click.echo("No buckets found.")

@s3.command()
@click.argument('bucket_name')
@click.option('--owner', required=True, help='Name of the owner')
@click.option('--project', required=True, help='Project name')
@click.option('--env', type=click.Choice(['dev', 'test', 'prod']), required=True, help='Environment')
@click.option('--public', is_flag=True, help='Make bucket public (READ ONLY)')
def create(bucket_name, owner, project, env, public):
    """Create a new S3 bucket."""
    s3_resource = boto3.resource('s3')
    
    if public:
        click.confirm(f"WARNING: You are about to make bucket '{bucket_name}' PUBLIC. Are you sure?", abort=True)
        acl = 'public-read'
    else:
        acl = 'private'

    click.echo(f"Creating {acl} bucket '{bucket_name}'...")

    try:
        session = boto3.session.Session()
        region = session.region_name
        
        create_params = {
            'Bucket': bucket_name,
            'ACL': acl
        }
        if region != 'us-east-1':
            create_params['CreateBucketConfiguration'] = {'LocationConstraint': region}

        bucket = s3_resource.create_bucket(**create_params)
        
        bucket_tagging = s3_resource.BucketTagging(bucket_name)
        bucket_tagging.put(
            Tagging={
                'TagSet': [
                    {'Key': TAG_NAME, 'Value': TAG_VALUE},
                    {'Key': 'Owner', 'Value': owner},
                    {'Key': 'Project', 'Value': project},
                    {'Key': 'Environment', 'Value': env}
                ]
            }
        )
        
        click.echo(f"Success! Bucket '{bucket_name}' created successfully.")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyExists':
            click.echo(f"Error: The bucket name '{bucket_name}' is already taken. Try a different name.")
        elif error_code == 'BucketAlreadyOwnedByYou':
            click.echo(f"Error: You already own a bucket named '{bucket_name}'.")
        else:
            click.echo(f"Error creating bucket: {e}")

@s3.command()
@click.argument('bucket_name')
@click.argument('file_path')
def upload(bucket_name, file_path):
    """Upload a file to an S3 bucket (only if created by CLI)."""
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    
    if not os.path.exists(file_path):
        click.echo(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        click.echo(f"Verifying bucket '{bucket_name}' ownership...")
        tag_set = bucket.Tagging().tag_set
        tags = {t['Key']: t['Value'] for t in tag_set}
        
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Bucket '{bucket_name}' was not created by this CLI. Access denied.")
            sys.exit(1)
            
        file_name = os.path.basename(file_path)
        click.echo(f"Uploading '{file_name}' to '{bucket_name}'...")
        
        bucket.upload_file(file_path, file_name)
        click.echo("Success! File uploaded.")
        
    except ClientError as e:
        click.echo(f"Error: {e}")


# --- Route53 Group ---
@cli.group()
def route53():
    """Manage Route53 DNS zones and records."""
    pass

@route53.command()
def list():
    """List CLI-created Hosted Zones."""
    client = boto3.client('route53')
    
    click.echo(f"Listing Hosted Zones with tag {TAG_NAME}={TAG_VALUE}...")
    
    try:
        response = client.list_hosted_zones()
        zones = response['HostedZones']
        
        found_any = False
        for zone in zones:
            zone_id = zone['Id'].split('/')[-1]
            zone_name = zone['Name']
            
            try:
                tags_response = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)
                tag_list = tags_response['ResourceTagSet']['Tags']
                tags = {t['Key']: t['Value'] for t in tag_list}
                
                if tags.get(TAG_NAME) == TAG_VALUE:
                    click.echo(f"- Zone ID: {zone_id}")
                    click.echo(f"  Name: {zone_name}")
                    click.echo(f"  Tags: Owner={tags.get('Owner')}, Env={tags.get('Environment')}")
                    found_any = True
                    
            except ClientError:
                continue
                
        if not found_any:
            click.echo("No CLI-created zones found.")
            
    except ClientError as e:
        click.echo(f"Error listing zones: {e}")

@route53.command()
@click.argument('zone_name')
@click.option('--owner', required=True, help='Name of the owner')
@click.option('--project', required=True, help='Project name')
@click.option('--env', type=click.Choice(['dev', 'test', 'prod']), required=True, help='Environment')
def create(zone_name, owner, project, env):
    """Create a new Route53 Hosted Zone."""
    client = boto3.client('route53')
    
    click.echo(f"Creating Hosted Zone '{zone_name}'...")

    try:
        caller_ref = f"{zone_name}-{int(time.time())}"
        
        response = client.create_hosted_zone(
            Name=zone_name,
            CallerReference=caller_ref,
            HostedZoneConfig={
                'Comment': f'Created by Platform CLI for {project} in {env}'
            }
        )
        
        full_zone_id = response['HostedZone']['Id']
        short_zone_id = full_zone_id.split('/')[-1]
        
        click.echo(f"Zone created! ID: {short_zone_id}")
        
        click.echo("Applying tags...")
        client.change_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=short_zone_id,
            AddTags=[
                {'Key': TAG_NAME, 'Value': TAG_VALUE},
                {'Key': 'Owner', 'Value': owner},
                {'Key': 'Project', 'Value': project},
                {'Key': 'Environment', 'Value': env}
            ]
        )
        
        click.echo("Success! Hosted Zone ready.")

    except ClientError as e:
        click.echo(f"Error: {e}")

@route53.command()
@click.argument('zone_id')
@click.argument('record_name')
@click.argument('record_value')
@click.option('--type', 'record_type', default='A', help='Record type (A, CNAME, etc.)')
def record(zone_id, record_name, record_value, record_type):
    """Create or update a DNS record in a CLI-created Zone."""
    client = boto3.client('route53')
    
    # בדיקת שייכות (Guardrail)
    try:
        tags_response = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)
        tag_list = tags_response['ResourceTagSet']['Tags']
        tags = {t['Key']: t['Value'] for t in tag_list}
        
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Zone {zone_id} was not created by this CLI. Access denied.")
            sys.exit(1)
            
    except ClientError as e:
        click.echo(f"Error checking zone tags: {e}")
        return

    click.echo(f"Creating/Updating record {record_name} -> {record_value} ({record_type}) in {zone_id}...")

    try:
        response = client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Comment': 'Managed by Platform CLI',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'TTL': 300,
                            'ResourceRecords': [{'Value': record_value}]
                        }
                    }
                ]
            }
        )
        click.echo("Success! Record change submitted.")
        click.echo(f"Status: {response['ChangeInfo']['Status']}")
        
    except ClientError as e:
        click.echo(f"Error creating record: {e}")

if __name__ == '__main__':
    cli()