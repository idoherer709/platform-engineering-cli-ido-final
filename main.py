import click
import boto3

# קבועים (Constants)
TAG_NAME = 'CreatedBy'
TAG_VALUE = 'platform-cli'
# שים לב: ה-AMI הזה מתאים ל-us-east-1 (N. Virginia). 
# אם אתה באזור אחר, תצטרך להחליף אותו.
AMI_ID = 'ami-0cff7528ff583bf9a' 

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
def create(owner, project, env):
    """Create a new EC2 instance."""
    ec2_resource = boto3.resource('ec2')
    
    # 1. בדיקה שאין חריגה מהמכסה (Hard Cap: 2)
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': f'tag:{TAG_NAME}', 'Values': [TAG_VALUE]}]
    )
    # סופרים רק שרתים שאינם במצב "terminated" (מחוקים)
    active_instances = [i for i in instances if i.state['Name'] != 'terminated']
    
    if len(active_instances) >= 2:
        click.echo("Error: Cannot create more than 2 instances via CLI (Hard Cap Reached).")
        return

    click.echo(f"Creating EC2 instance for {owner} in {env}...")

    # 2. יצירת השרת בפועל
    try:
        new_instances = ec2_resource.create_instances(
            ImageId=AMI_ID,
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro', # סוג השרת (הכי זול/חינמי)
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': TAG_NAME, 'Value': TAG_VALUE},
                        {'Key': 'Owner', 'Value': owner},
                        {'Key': 'Project', 'Value': project},
                        {'Key': 'Environment', 'Value': env},
                        {'Key': 'Name', 'Value': f"{project}-{env}-server"} # שם שיהיה נוח לראות בקונסול
                    ]
                }
            ]
        )
        
        instance = new_instances[0]
        click.echo("Waiting for instance to start running...")
        instance.wait_until_running() # ממתין שהשרת יעלה
        instance.reload() # מרענן את המידע כדי לקבל את הכתובת IP וכו'
        
        click.echo(f"Success! Instance created.")
        click.echo(f"ID: {instance.id}")
        click.echo(f"State: {instance.state['Name']}")
        
    except Exception as e:
        click.echo(f"Error creating instance: {e}")

@ec2.command()
def list():
    """List CLI-created instances."""
    ec2_resource = boto3.resource('ec2')
    
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
        # הצגת התגיות הנוספות לביקורת
        tags_dict = {tag['Key']: tag['Value'] for tag in instance.tags}
        click.echo(f"  Tags: Owner={tags_dict.get('Owner')}, Env={tags_dict.get('Environment')}")
        count += 1
    
    if count == 0:
        click.echo("No active instances found.")

if __name__ == '__main__':
    cli()