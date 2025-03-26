import argparse
import boto3
import json
import uuid
from datetime import datetime

class CustomerManager:
    def __init__(self, region_name='us-east-1'):
        self.apigateway = boto3.client('apigateway', region_name=region_name)
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        
        # Ensure customer table exists
        self.customer_table_name = 'bedrock_customers'
        self._ensure_customer_table_exists()
    
    def _ensure_customer_table_exists(self):
        """Create the customers table if it doesn't exist"""
        existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
        
        if self.customer_table_name not in existing_tables:
            print(f"Creating {self.customer_table_name} table...")
            table = self.dynamodb.create_table(
                TableName=self.customer_table_name,
                KeySchema=[
                    {'AttributeName': 'customer_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'customer_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            table.wait_until_exists()
            print(f"Table {self.customer_table_name} created successfully.")
    
    def create_customer(self, name, email, usage_plan_id):
        """Create a new customer with API key"""
        # Generate a unique customer ID
        customer_id = str(uuid.uuid4())
        
        # Create API key for the customer
        key_response = self.apigateway.create_api_key(
            name=f"customer_{name.replace(' ', '_').lower()}",
            description=f"API Key for {name}",
            enabled=True
        )
        
        api_key_id = key_response['id']
        api_key_value = key_response['value']
        
        # Associate API key with usage plan
        self.apigateway.create_usage_plan_key(
            usagePlanId=usage_plan_id,
            keyId=api_key_id,
            keyType='API_KEY'
        )
        
        # Store customer information in DynamoDB
        customer_table = self.dynamodb.Table(self.customer_table_name)
        customer_table.put_item(
            Item={
                'customer_id': customer_id,
                'name': name,
                'email': email,
                'api_key_id': api_key_id,
                'created_at': datetime.now().isoformat(),
                'status': 'active',
                'usage_plan_id': usage_plan_id
            }
        )
        
        print(f"Customer created successfully:")
        print(f"Customer ID: {customer_id}")
        print(f"API Key: {api_key_value}")
        
        return {
            'customer_id': customer_id,
            'api_key': api_key_value
        }
    
    def list_customers(self):
        """List all customers"""
        customer_table = self.dynamodb.Table(self.customer_table_name)
        response = customer_table.scan()
        customers = response.get('Items', [])
        
        print(f"Found {len(customers)} customers:")
        for customer in customers:
            print(f"ID: {customer['customer_id']}, Name: {customer['name']}, Email: {customer['email']}")
        
        return customers
    
    def get_customer_usage(self, customer_id, start_date=None, end_date=None):
        """Get usage statistics for a customer"""
        # Get the customer record to find API key ID
        customer_table = self.dynamodb.Table(self.customer_table_name)
        customer = customer_table.get_item(Key={'customer_id': customer_id}).get('Item')
        
        if not customer:
            print(f"Customer with ID {customer_id} not found")
            return None
        
        api_key_id = customer['api_key_id']
        usage_plan_id = customer['usage_plan_id']
        
        # Get usage data from API Gateway
        usage_response = self.apigateway.get_usage(
            usagePlanId=usage_plan_id,
            keyId=api_key_id,
            startDate=start_date or '2023-01-01',
            endDate=end_date or datetime.now().strftime('%Y-%m-%d')
        )
        
        print(f"Usage for {customer['name']} ({customer_id}):")
        print(json.dumps(usage_response.get('items', {}), indent=2))
        
        return usage_response

def main():
    parser = argparse.ArgumentParser(description='Manage Bedrock API customers')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create customer command
    create_parser = subparsers.add_parser('create', help='Create a new customer')
    create_parser.add_argument('--name', required=True, help='Customer name')
    create_parser.add_argument('--email', required=True, help='Customer email')
    create_parser.add_argument('--usage-plan-id', required=True, help='Usage plan ID')
    
    # List customers command
    subparsers.add_parser('list', help='List all customers')
    
    # Get usage command
    usage_parser = subparsers.add_parser('usage', help='Get customer usage')
    usage_parser.add_argument('--customer-id', required=True, help='Customer ID')
    usage_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    usage_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    manager = CustomerManager()
    
    if args.command == 'create':
        manager.create_customer(args.name, args.email, args.usage_plan_id)
    elif args.command == 'list':
        manager.list_customers()
    elif args.command == 'usage':
        manager.get_customer_usage(args.customer_id, args.start_date, args.end_date)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
