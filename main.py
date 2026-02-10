import click
import boto3
import sys

# קבועים (Constants)
TAG_NAME = 'CreatedBy'
TAG_VALUE = 'platform-cli'

def get_latest_ami():
    """
    Helper function to get the latest Amazon Linux 2 AMI ID 
    from AWS Systems Manager (SSM) Parameter Store.
    """
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
@click.option('--type', 'instance_type', type=click.Choice(['t2.micro', 't3.micro']), default='t2.micro', help='Instance type (t2.micro or t3.micro)')
def create(owner, project, env, instance_type):
    """Create a new EC2 instance."""
    ec2_resource = boto3.resource('ec2')
    
    # 1. בדיקת מכסה (Hard Cap: 2)
    # סופרים כמה שרתים פעילים כבר יש לנו עם התגית שלנו
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': f'tag:{TAG_NAME}', 'Values': [TAG_VALUE]}]
    )
    active_instances = [i for i in instances if i.state['Name'] != 'terminated']
    
    if len(active_instances) >= 2:
        click.echo("Error: Cannot create more than 2 instances via CLI (Hard Cap Reached).")
        return

    # 2. השגת ה-AMI העדכני ביותר באופן דינמי
    click.echo("Fetching latest Amazon Linux 2 AMI...")
    try:
        ami_id = get_latest_ami()
        click.echo(f"Found AMI: {ami_id}")
    except Exception as e:
        click.echo(f"Error fetching AMI: {e}")
        return

    click.echo(f"Creating EC2 instance ({instance_type}) for {owner} in {env}...")

    # 3. יצירת השרת בפועל
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
    
    # סינון: רק שרתים שהכלי הזה יצר
    instances = ec2_resource.instances.filter(
        Filters=[
            {'Name': f'tag:{TAG_NAME}', 'Values': [TAG_VALUE]}
        ]
    )

    click.echo(f"Listing instances with tag {TAG_NAME}={TAG_VALUE}...")
    
    count = 0
    for instance in instances:
        # מדלגים על שרתים מחוקים בתצוגה
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
    """Stop an EC2 instance (only if created by CLI)."""
    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)

    try:
        # בדיקה שהשרת קיים ושייך לנו (Tag Validation)
        instance.load() # טוען את המידע עליו
        tags = {t['Key']: t['Value'] for t in instance.tags or []}
        
        # אבטחה: אם התגית לא קיימת או לא תואמת, חוסמים את הפעולה
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Instance {instance_id} was not created by this CLI. Access denied.")
            sys.exit(1)
            
        click.echo(f"Stopping instance {instance_id}...")
        instance.stop()
        instance.wait_until_stopped()
        click.echo(f"Instance {instance_id} stopped successfully.")
        
    except Exception as e:
        click.echo(f"Error: {e}")

@ec2.command()
@click.argument('instance_id')
def start(instance_id):
    """Start an EC2 instance (only if created by CLI)."""
    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)

    try:
        # בדיקה שהשרת קיים ושייך לנו
        instance.load()
        tags = {t['Key']: t['Value'] for t in instance.tags or []}
        
        if tags.get(TAG_NAME) != TAG_VALUE:
            click.echo(f"Error: Instance {instance_id} was not created by this CLI. Access denied.")
            sys.exit(1)
            
        click.echo(f"Starting instance {instance_id}...")
        instance.start()
        instance.wait_until_running()
        click.echo(f"Instance {instance_id} is now running.")
        
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli()