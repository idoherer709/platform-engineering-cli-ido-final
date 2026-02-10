# Platform CLI - Demo Evidence

## EC2 Operations

### 1. Create Instance
Command: `python main.py ec2 create --owner Ido --project Demo1 --env dev`
Output:
Creating EC2 instance for Ido in dev...
Waiting for instance to start running...
Success! Instance created.
ID: i-0abffadbb120e4bf7
State: running

### 2. List Instances
Command: `python main.py ec2 list`
Output:
Listing instances with tag CreatedBy=platform-cli...
- ID: i-0abffadbb120e4bf7, Type: t2.micro, State: running
  Tags: Owner=Ido, Env=dev

  