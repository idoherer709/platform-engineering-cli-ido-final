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

  ### 3. Stop Instance
Command: `python main.py ec2 stop i-04c62ec8327c1cc7e`
Output:
Stopping instance i-04c62ec8327c1cc7e...
Instance i-04c62ec8327c1cc7e stopped successfully.


### 4. Start Instance
Command: `python main.py ec2 start i-04c62ec8327c1cc7e`
Output:
Starting instance i-04c62ec8327c1cc7e...
Instance i-04c62ec8327c1cc7e is now running.


## S3 Operations

### 1. Create Private Bucket
Command: `python main.py s3 create platform-cli-ido-test-1 --owner Ido --project DemoS3 --env dev`
Output:
Creating private bucket 'platform-cli-ido-test-1'...
Success! Bucket 'platform-cli-ido-test-1' created successfully.

### 2. Create Public Bucket (Guardrail Check)
Command: `python main.py s3 create platform-cli-ido-public-1 --owner Ido --project DemoS3 --env dev --public`
Output:
WARNING: You are about to make bucket 'platform-cli-ido-public-1' PUBLIC. Are you sure? [y/N]: N
Aborted!


### 3. Upload File (Ownership Check)
Command: `python main.py s3 upload platform-cli-ido-test-1 hello.txt`
Output:
Verifying bucket 'platform-cli-ido-test-1' ownership...
Uploading 'hello.txt' to 'platform-cli-ido-test-1'...
Success! File uploaded.

