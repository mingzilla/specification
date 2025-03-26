# Commercial Customer Usage Tracking for AWS Bedrock Lambda Proxy

## Table of Contents
- [Commercial Customer Usage Tracking for AWS Bedrock Lambda Proxy](#commercial-customer-usage-tracking-for-aws-bedrock-lambda-proxy)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Solution Architecture](#solution-architecture)
  - [Setup Guide](#setup-guide)
    - [API Gateway Configuration](#api-gateway-configuration)
    - [Customer Management System](#customer-management-system)
    - [Analytics Infrastructure](#analytics-infrastructure)
  - [Customer Management Workflow](#customer-management-workflow)
    - [Adding a New Customer](#adding-a-new-customer)
    - [Listing Customers](#listing-customers)
    - [Checking Customer Usage](#checking-customer-usage)
  - [Reporting and Billing](#reporting-and-billing)
    - [Creating Dashboards](#creating-dashboards)
    - [Billing Process Example](#billing-process-example)
  - [Client Integration](#client-integration)
    - [Javascript](#javascript)
    - [Python](#python)
    - [cURL](#curl)
  - [Maintenance and Operations](#maintenance-and-operations)
    - [Regular Maintenance Tasks](#regular-maintenance-tasks)
    - [Troubleshooting Common Issues](#troubleshooting-common-issues)
  - [Security Best Practices](#security-best-practices)

## Overview

This document provides a comprehensive guide for implementing commercial customer usage tracking for this [AWS Bedrock Lambda Proxy service](../2025-03-26_bed-rock-proxy/bedrock-lambda-proxy.md). The solution leverages AWS API Gateway with a DynamoDB-based token management system to track customer usage with Bearer token authentication, following AWS-native patterns and community standards.

**Key Components:**
- API Gateway as the HTTP endpoint
- Lambda Proxy with Bearer token authentication
- Customer management system using DynamoDB
- Automated analytics infrastructure with CloudWatch, S3, Glue, and QuickSight
- Client-side integration examples for your customers

This solution allows you to:
1. Generate unique Bearer tokens for each customer
2. Track usage per customer for billing purposes
3. Implement various pricing models (pay-per-request, tiered, subscription)
4. Generate detailed usage reports and visualizations

## Solution Architecture

The architecture diagram below illustrates how the components interact:

![API Gateway Usage Tracking Architecture](architecture-diagram.png)

- Ref: [API Gateway Usage Tracking Architecture](architecture-diagram.mermaid)

**Architecture Components:**
- **Client Applications**: Use Bearer tokens to authenticate
- **API Gateway**: Routes requests to the Lambda function
- **Lambda Function**: Validates Bearer tokens and logs usage
- **AWS Bedrock**: Provides the underlying model services
- **Analytics Pipeline**: CloudWatch → S3 → Glue → Database → QuickSight
- **Admin Dashboard**: For managing customers and viewing reports

## Setup Guide

### API Gateway Configuration

- [api-gateway-setup.sh](api-gateway-setup.sh)

The `api-gateway-setup.sh` script automates the creation of:
- A REST API endpoint
- A resource and POST method that passes through the Authorization header
- Integration with your Lambda function

**Setup Steps:**

1. Edit the script to update your region and Lambda ARN:
   ```bash
   # Open the file
   nano api-gateway-setup.sh
   
   # Update these values
   LAMBDA_ARN="arn:aws:lambda:REGION:ACCOUNT_ID:function:bedrock-proxy"
   REGION="us-east-1"  # Your AWS region
   ```

2. Make the script executable and run it:
   ```bash
   chmod +x api-gateway-setup.sh
   ./api-gateway-setup.sh
   ```

3. Note the API endpoint URL that is output. You'll need this for client integration.

### Customer Management System

- [customer-management.py](customer-management.py)

The `customer-management.py` script provides a CLI tool for managing customers and their Bearer tokens.

**Setup Steps:**

1. Install the required Python dependencies:
   ```bash
   pip install boto3
   ```

2. Make sure your AWS credentials are configured:
   ```bash
   aws configure
   ```

3. The script will automatically create a DynamoDB table named `bedrock_customers` on first run.

### Analytics Infrastructure

- [reporting-setup.yml](reporting-setup.yml)

Deploy the CloudFormation template (`reporting-setup.yml`) to set up the analytics infrastructure:

1. Deploy the template:
   ```bash
   aws cloudformation create-stack \
     --stack-name bedrock-usage-analytics \
     --template-body file://reporting-setup.yml \
     --capabilities CAPABILITY_IAM
   ```

2. Once deployment is complete, note the S3 bucket name and Glue database name from the outputs.

3. Set up Amazon QuickSight (if not already configured):
   - Sign up for QuickSight in the AWS Console
   - Create a new dataset using AWS Glue as the source
   - Connect to the `bedrock_usage_db` database

## Customer Management Workflow

### Adding a New Customer

When onboarding a new customer:

1. Create a Bearer token for the customer:
   ```bash
   python customer-management.py create \
     --name "Customer Name" \
     --email "customer@example.com"
   ```

2. The script will output a customer ID and Bearer token. Provide this token to your customer along with integration instructions.

3. Optionally, generate a more secure token:
   ```bash
   # Generate a secure token
   TOKEN=$(openssl rand -base64 32)
   
   # Create customer with specified token
   python customer-management.py create \
     --name "Customer Name" \
     --email "customer@example.com" \
     --token "$TOKEN"
   ```

### Listing Customers

To view all registered customers:

```bash
python customer-management.py list
```

This command displays all customers stored in your DynamoDB table, including their customer IDs, names, and email addresses.

### Checking Customer Usage

To retrieve usage statistics for a specific customer:

```bash
python customer-management.py usage \
  --customer-id "12345678-1234-1234-1234-123456789012" \
  --start-date "2023-04-01" \
  --end-date "2023-04-30"
```

This retrieves the number of API calls made by the customer within the specified date range, useful for billing purposes.

## Reporting and Billing

The reporting infrastructure automatically:

1. Exports daily usage data from CloudWatch Logs to the S3 bucket (runs at 1:00 AM UTC)
2. Updates the Glue catalog (runs at 2:00 AM UTC)
3. Makes the data available for querying through Athena or QuickSight

### Creating Dashboards

In Amazon QuickSight:

1. Create a new analysis using the `bedrock_usage_db` database
2. Build visualizations such as:
   - API calls per customer per day
   - Total usage by customer (monthly view)
   - Usage trends over time
   - Most active customers

### Billing Process Example

A typical monthly billing workflow:

1. At the end of each billing period, query the usage data:
   ```bash
   # Using the script
   python customer-management.py usage \
     --customer-id "CUSTOMER_ID" \
     --start-date "BILLING_START" \
     --end-date "BILLING_END"
   
   # Or query the data in Athena/QuickSight
   ```

2. Apply your pricing model:
   - Pay-per-request: Multiply requests by your per-request rate
   - Tiered pricing: Apply different rates based on usage volume
   - Subscription + overage: Charge fixed amount plus overage fees

3. Generate invoices based on the calculated amounts

## Client Integration

### Javascript

```js
// JavaScript Example (Browser/Node.js)
async function callBedrockAPI(prompt) {
  const apiEndpoint = 'https://your-api-gateway-url/prod/bedrock';
  const authToken = 'your-customer-token-here';
  
  const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      // Required: specify which model to use
      modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
      
      // Claude-specific parameters
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: prompt
            }
          ]
        }
      ]
    })
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return await response.json();
}

// Example usage
// callBedrockAPI("What is the capital of France?")
//   .then(result => console.log(result))
//   .catch(error => console.error(error));
```

### Python

```python
import requests

def call_bedrock_api(prompt):
    api_endpoint = "https://your-api-gateway-url/prod/bedrock"
    auth_token = "your-customer-token-here"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    payload = {
        "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    response = requests.post(api_endpoint, headers=headers, json=payload)
    response.raise_for_status()  # Raise exception for 4XX/5XX responses
    
    return response.json()

# Example usage
# try:
#     result = call_bedrock_api("What is the capital of France?")
#     print(result)
# except Exception as e:
#     print(f"Error: {e}")
```

### cURL

```sh
curl -X POST https://your-api-gateway-url/prod/bedrock \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-customer-token-here" \
  -d '{
    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text", 
            "text": "What is the capital of France?"
          }
        ]
      }
    ]
  }'
```

## Maintenance and Operations

### Regular Maintenance Tasks

1. **Bearer Token Rotation**:
   Implement a policy for rotating tokens periodically:
   ```bash
   # Process for rotating a customer's token
   # 1. Generate a new secure token
   NEW_TOKEN=$(openssl rand -base64 32)
   
   # 2. Update the token in your database
   python customer-management.py update-token \
     --customer-id "CUSTOMER_ID" \
     --token "$NEW_TOKEN"
   
   # 3. Provide to customer
   # 4. After customer confirms migration, invalidate old token
   ```

2. **Usage Monitoring**:
   Periodically review usage patterns and set appropriate limits in the Lambda function:
   ```bash
   # Update customer rate limits in DynamoDB
   python customer-management.py update-limits \
     --customer-id "CUSTOMER_ID" \
     --daily-limit 1000
   ```

3. **Monitoring and Alerts**:
   Set up CloudWatch alarms for:
   - High error rates
   - Excessive usage
   - Unusual usage patterns

### Troubleshooting Common Issues

1. **Authentication Issues**:
   - Verify the Bearer token is valid and correctly formatted
   - Check if the customer's token has been rotated
   - Ensure the Authorization header is being correctly passed through API Gateway

2. **Usage Data Not Appearing**:
   - Check CloudWatch logs for the export Lambda function
   - Verify the Glue crawler is running successfully
   - Check IAM permissions

3. **High Latency**:
   - Check Lambda concurrency limits
   - Monitor Bedrock model response times
   - Consider adjusting Lambda memory allocation

## Security Best Practices

1. **Token Management**:
   - Generate tokens using cryptographically secure methods
   - Never store tokens in code repositories
   - Implement token rotation procedures
   - Use a secure method to distribute tokens to customers

2. **Access Controls**:
   - Implement least privilege IAM policies
   - Restrict access to the customer management script
   - Use AWS CloudTrail to audit administrative actions

3. **Data Protection**:
   - Encrypt data at rest in S3 and DynamoDB
   - Implement TLS for all communications
   - Consider implementing VPC endpoints for AWS services

---

**Note**: This solution follows AWS best practices and community standards for implementing a commercial model for AWS Bedrock access. It is designed to be low-maintenance, scalable, and compatible with your existing Lambda function's Bearer token authentication.