# Platform Engineering CLI 🛠️

A comprehensive CLI tool for managing AWS resources (EC2, S3, Route53) with built-in guardrails and automatic tagging. Built with Python, `click`, and `boto3`.

## 🚀 Features

* **Global Tagging:** Automatically tags all resources with `Owner`, `Environment`, and `Project`.
* **Guardrails:**
    * Limits EC2 instances to a maximum of 2.
    * Prevents accidental creation of public S3 buckets (requires confirmation).
    * Restricts operations (Stop/Start/Upload) to resources created by this CLI only.

## 📦 Components

### 1. Compute (EC2) 🖥️
* **Create:** Deploys `t2.micro` or `t3.micro` instances. Automatically fetches the latest Amazon Linux 2 AMI.
* **Manage:** Start and Stop instances safely.
* **List:** View details of active instances managed by the CLI.

### 2. Storage (S3) 🪣
* **Create:** Supports Private and Public buckets.
* **Upload:** Securely upload files to CLI-managed buckets.
* **List:** View buckets and their tags.

### 3. Network (Route53) 🌐
* **Hosted Zones:** Create and tag new DNS zones.
* **Records:** Upsert 'A' records for your domains.
* **List:** View managed zones.

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/idoherer709/platform-engineering-cli-ido-final.git](https://github.com/idoherer709/platform-engineering-cli-ido-final.git)
    cd platform-engineering-cli-ido-final
    ```

2.  **Set up Virtual Environment:**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install click boto3
    ```

4.  **Configure AWS Credentials:**
    Make sure you have your AWS credentials set up (via `aws configure` or environment variables).

## 📖 Usage Examples

Here is a comprehensive list of all available commands.

### 🖥️ EC2 Operations ###

# 1. Create a new instance
# Create a default t2.micro instance
python main.py ec2 create --owner Ido --project Demo --env dev

# Create a specific t3.micro instance
python main.py ec2 create --owner Ido --project Demo --env prod --type t3.micro

# 2. List instances (Shows only instances created by this CLI tool)
python main.py ec2 list

# 3. Manage Power State (Replace instance ID with actual ID)
# Stop an instance
python main.py ec2 stop i-0123456789abcdef0
# Start an instance
python main.py ec2 start i-0123456789abcdef0


### 🪣 S3 Operations ###

# 1. Create a Bucket (Names must be globally unique)
# Create a Private bucket (Default)
python main.py s3 create my-unique-bucket-name --owner Ido --project Demo --env dev
# Create a Public bucket (Will prompt for confirmation)
python main.py s3 create my-public-bucket --owner Ido --project Demo --env dev --public

# 2. List Buckets
python main.py s3 list

# 3. Upload a File (Verifies ownership before uploading)
# Usage: python main.py s3 upload <BUCKET_NAME> <LOCAL_FILE_PATH>
python main.py s3 upload my-unique-bucket-name ./hello.txt


### 🌐 Route53 Operations ###

# 1. Create a Hosted Zone (Tags it automatically)
python main.py route53 create my-app.com --owner Ido --project Demo --env dev

# 2. List Hosted Zones
python main.py route53 list

# 3. Manage DNS Records (Creates or updates/Upsert an 'A' record)
# Usage: python main.py route53 record <ZONE_ID> <RECORD_NAME> <IP_ADDRESS>
python main.py route53 record Z12345ABCDE www.my-app.com 54.123.45.67

## 🏷️ Tagging Convention

Resources created by this tool are automatically tagged to ensure governance and cost tracking.

| Tag Key | Value | Description |
| :--- | :--- | :--- |
| `CreatedBy` | `platform-cli` | Identifies resources managed by this tool. |
| `Owner` | `<user_input>` | The person responsible for the resource. |
| `Project` | `<user_input>` | The project associated with the resource. |
| `Environment` | `dev` / `test` / `prod` | The deployment environment. |

## 🧹 Cleanup Resources

**Important:** This CLI tool creates real AWS resources that cost money. Since the tool currently focuses on *creation* and *management*, full deletion must be done via the AWS Console or AWS CLI.

To avoid unexpected charges, follow these steps after testing:

1.  **EC2 Instances:**
    * Go to the EC2 Console.
    * Select instances tagged with `CreatedBy=platform-cli`.
    * Action: **Terminate Instance**.

2.  **S3 Buckets:**
    * Go to the S3 Console.
    * Select buckets created by the tool.
    * Action: **Empty** the bucket first, then **Delete**.

3.  **Route53 Zones:**
    * Go to the Route53 Console.
    * Select the Hosted Zones you created.
    * Action: **Delete Zone** (Ensure all non-default records are deleted first).