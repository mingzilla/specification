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
    - [Integration Instructions for Customers](#integration-instructions-for-customers)
    - [SDK/Client Customization](#sdkclient-customization)
  - [Maintenance and Operations](#maintenance-and-operations)
    - [Regular Maintenance Tasks](#regular-maintenance-tasks)
    - [Troubleshooting Common Issues](#troubleshooting-common-issues)
  - [Security Best Practices](#security-best-practices)

## Overview

This document provides a comprehensive guide for implementing commercial customer usage tracking for this [AWS Bedrock Lambda Proxy service](../2025-03-26_bed-rock-proxy/bedrock-lambda-proxy.md). The solution leverages AWS API Gateway with Usage Plans to track customer usage without modifying your existing Lambda function, following AWS-native patterns and community standards.


**Key Components:**
- API Gateway with Usage Plans for authentication and usage tracking
- Customer management system using DynamoDB
- Automated analytics infrastructure with S3, Glue, and QuickSight
- Client-side integration example for your customers

This solution allows you to:
1. Generate unique API keys for each customer
2. Track usage per customer for billing purposes
3. Set quotas and throttling limits per customer
4. Implement various pricing models (pay-per-request, tiered, subscription)
5. Generate detailed usage reports and visualizations

## Solution Architecture

The architecture diagram below illustrates how the components interact:

![API Gateway Usage Tracking Architecture](architecture-diagram.png)

- Ref: [API Gateway Usage Tracking Architecture](architecture-diagram.mermaid)

**Architecture Components:**
- **Client Applications**: Use API keys to authenticate
- **API Gateway**: Manages authentication and tracks usage via API keys and Usage Plans
- **Lambda Function**: Your existing Bedrock proxy (no changes needed)
- **AWS Bedrock**: Provides the underlying model services
- **Analytics Pipeline**: CloudWatch → S3 → Glue → Database → QuickSight
- **Admin Dashboard**: For managing customers and viewing reports

## Setup Guide

### API Gateway Configuration

- [API Gateway Setup Script](api-gateway-setup.sh)

The `api-gateway-setup.sh` script automates the creation of:
- A REST API endpoint
- A resource and POST method requiring an API key
- Integration with your Lambda function
- A default usage plan with throttling and quotas

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

3. Note the API endpoint URL and Usage Plan ID that are output. You'll need these for the next steps.

### Customer Management System

- [Customer Management Script](customer-management.py)

The `customer-management.py` script provides a CLI tool for managing customers and their API keys.

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

- [Reporting Infrastructure Template](reporting-setup.yml)

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

1. Create an API key for the customer:
   ```bash
   python customer-management.py create \
     --name "Customer Name" \
     --email "customer@example.com" \
     --usage-plan-id "a1b2c3d4"  # Your Usage Plan ID from API Gateway setup
   ```

2. The script will output a customer ID and API key. Provide this API key to your customer along with integration instructions.

3. Optionally, customize the usage plan for this customer if they need different limits:
   ```bash
   # Create a custom usage plan in API Gateway Console or via AWS CLI
   aws apigateway create-usage-plan \
     --name "Premium-Plan-CustomerName" \
     --throttle "rateLimit=20,burstLimit=40" \
     --quota "limit=5000,period=MONTH"
   
   # Then associate the customer's API key with this new plan
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

1. Exports daily usage data to the S3 bucket (runs at 1:00 AM UTC)
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

- [Client Integration Example](client-integration.js)

Provide your customers with the `client-integration.js` file as a reference for integrating with your API. This JavaScript client encapsulates the API calls to your Bedrock proxy service.

### Integration Instructions for Customers

1. Include the client in your application:
   ```javascript
   // Browser
   <script src="bedrock-client.js"></script>
   
   // Node.js
   const { BedrockClient } = require('./bedrock-client.js');
   ```

2. Initialize the client with your API key:
   ```javascript
   const client = new BedrockClient({
     apiEndpoint: 'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/bedrock',
     apiKey: 'YOUR_API_KEY_HERE',
     defaultModel: 'anthropic.claude-3-sonnet-20240229-v1:0'
   });
   ```

3. Make calls to Bedrock models:
   ```javascript
   const response = await client.callModel({
     messages: [
       {
         role: 'user',
         content: [
           {
             type: 'text',
             text: 'What is the capital of France?'
           }
         ]
       }
     ]
   });
   ```

### SDK/Client Customization

The provided client supports different model types (Claude, Llama, etc.) and handles the appropriate payload formatting. You can customize it to:
- Add logging
- Include additional models
- Implement retry logic
- Add application-specific authentication

## Maintenance and Operations

### Regular Maintenance Tasks

1. **API Key Rotation**:
   Implement a policy for rotating API keys periodically:
   ```bash
   # Process for rotating a customer's API key
   # 1. Create a new API key
   # 2. Associate it with the usage plan
   # 3. Provide to customer
   # 4. After customer confirms migration, delete old key
   ```

2. **Usage Plan Adjustments**:
   Periodically review and adjust quotas and throttling based on usage patterns:
   ```bash
   aws apigateway update-usage-plan \
     --usage-plan-id "USAGE_PLAN_ID" \
     --patch-operations "op=replace,path=/quota/limit,value=2000"
   ```

3. **Monitoring and Alerts**:
   Set up CloudWatch alarms for:
   - API throttling events
   - Approaching quota limits
   - Unusual usage patterns

### Troubleshooting Common Issues

1. **API Keys Not Working**:
   - Verify the key is associated with the correct usage plan
   - Check if the customer has exceeded their quota
   - Ensure the API method requires an API key

2. **Usage Data Not Appearing**:
   - Check CloudWatch logs for the export Lambda function
   - Verify the Glue crawler is running successfully
   - Check IAM permissions

3. **High Latency**:
   - Review API Gateway caching settings
   - Check Lambda concurrency limits
   - Monitor Bedrock model response times

## Security Best Practices

1. **API Key Management**:
   - Never store API keys in code repositories
   - Implement key rotation procedures
   - Use a secure method to distribute keys to customers

2. **Access Controls**:
   - Implement least privilege IAM policies
   - Restrict access to the customer management script
   - Use AWS CloudTrail to audit administrative actions

3. **Data Protection**:
   - Encrypt data at rest in S3 and DynamoDB
   - Implement TLS for all communications
   - Consider implementing VPC endpoints for AWS services

---

**Note**: This solution follows AWS best practices and community standards for implementing a commercial model for AWS Bedrock access. It is designed to be low-maintenance, scalable, and requires no changes to your existing Lambda function.
