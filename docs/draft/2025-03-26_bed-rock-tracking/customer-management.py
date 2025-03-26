import argparse
import boto3
import json
import uuid
import secrets
import base64
from datetime import datetime

class CustomerManager:
    def __init__(self, region_name='us-east-1'):
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.cloudwatch = boto3.client('logs', region_name=region_name)
        
        # Ensure customer table exists
        self.customer_table_name = 'bedrock_customers'
        self.token_table_name = 'bedrock_tokens'
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create the required tables if they don't exist"""
        existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
        
        # Create customers table if it doesn't exist
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
        
        # Create tokens table if it doesn't exist
        if self.token_table_name not in existing_tables:
            print(f"Creating {self.token_table_name} table...")
            table = self.dynamodb.create_table(
                TableName=self.token_table_name,
                KeySchema=[
                    {'AttributeName': 'token', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'token', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            table.wait_until_exists()
            print(f"Table {self.token_table_name} created successfully.")
    
    def generate_token(self):
        """Generate a secure random token"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    def create_customer(self, name, email, token=None):
        """Create a new customer with a Bearer token"""
        # Generate a unique customer ID
        customer_id = str(uuid.uuid4())
        
        # Generate a token if not provided
        if not token:
            token = self.generate_token()
        
        # Store customer information in DynamoDB
        customer_table = self.dynamodb.Table(self.customer_table_name)
        customer_table.put_item(
            Item={
                'customer_id': customer_id,
                'name': name,
                'email': email,
                'created_at': datetime.now().isoformat(),
                'status': 'active',
                'current_token': token,
                'rate_limit_daily': 1000  # Default daily request limit
            }
        )
        
        # Store token mapping
        token_table = self.dynamodb.Table(self.token_table_name)
        token_table.put_item(
            Item={
                'token': token,
                'customer_id': customer_id,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
        )
        
        print(f"Customer created successfully:")
        print(f"Customer ID: {customer_id}")
        print(f"Bearer Token: {token}")
        
        return {
            'customer_id': customer_id,
            'token': token
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
    
    def rotate_token(self, customer_id):
        """Rotate a customer's token"""
        # Get the customer record
        customer_table = self.dynamodb.Table(self.customer_table_name)
        customer = customer_table.get_item(Key={'customer_id': customer_id}).get('Item')
        
        if not customer:
            print(f"Customer with ID {customer_id} not found")
            return None
        
        # Get the current token
        current_token = customer.get('current_token')
        
        # Generate a new token
        new_token = self.generate_token()
        
        # Update the customer record
        customer_table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression='SET current_token = :token, previous_token = :old_token',
            ExpressionAttributeValues={
                ':token': new_token,
                ':old_token': current_token
            }
        )
        
        # Add the new token mapping
        token_table = self.dynamodb.Table(self.token_table_name)
        token_table.put_item(
            Item={
                'token': new_token,
                'customer_id': customer_id,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
        )
        
        # Mark the old token as deprecated (but still valid for a grace period)
        if current_token:
            token_table.update_item(
                Key={'token': current_token},
                UpdateExpression='SET status = :status',
                ExpressionAttributeValues={
                    ':status': 'deprecated'
                }
            )
        
        print(f"Token rotated successfully for {customer['name']}:")
        print(f"New Bearer Token: {new_token}")
        
        return {
            'customer_id': customer_id,
            'new_token': new_token,
            'old_token': current_token
        }
    
    def update_limits(self, customer_id, daily_limit):
        """Update a customer's usage limits"""
        customer_table = self.dynamodb.Table(self.customer_table_name)
        
        response = customer_table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression='SET rate_limit_daily = :limit',
            ExpressionAttributeValues={
                ':limit': daily_limit
            },
            ReturnValues='UPDATED_NEW'
        )
        
        print(f"Updated daily limit for customer {customer_id} to {daily_limit} requests")
        return response
    
    def get_customer_usage(self, customer_id, start_date=None, end_date=None):
        """Get usage statistics for a customer from CloudWatch Logs"""
        # Get the customer record
        customer_table = self.dynamodb.Table(self.customer_table_name)
        customer = customer_table.get_item(Key={'customer_id': customer_id}).get('Item')
        
        if not customer:
            print(f"Customer with ID {customer_id} not found")
            return None
        
        # Format dates
        if not start_date:
            start_date = (datetime.now().replace(day=1)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Convert dates to timestamps
        start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        # Query CloudWatch Logs
        # Note: You'll need to set up your Lambda to log with customer_id for this to work
        try:
            log_group_name = '/aws/lambda/bedrock-proxy'  # Update with your Lambda log group
            
            query = f"fields @timestamp, @message | filter customer_id = '{customer_id}' | stats count() by bin(1h)"
            
            start_query_response = self.cloudwatch.start_query(
                logGroupName=log_group_name,
                startTime=start_timestamp,
                endTime=end_timestamp,
                queryString=query
            )
            
            query_id = start_query_response['queryId']
            
            # Get query results
            response = None
            while response is None or response['status'] == 'Running':
                print('Waiting for query to complete...')
                response = self.cloudwatch.get_query_results(
                    queryId=query_id
                )
            
            results = response['results']
            
            # Process and display results
            print(f"Usage for {customer['name']} ({customer_id}) from {start_date} to {end_date}:")
            
            total_requests = 0
            if results:
                for result in results:
                    count = next((field['value'] for field in result if field['field'] == 'count()'), '0')
                    total_requests += int(count)
                
                print(f"Total requests: {total_requests}")
            else:
                print("No usage data found")
            
            return {
                'customer_id': customer_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_requests': total_requests,
                'detailed_results': results
            }
            
        except Exception as e:
            print(f"Error getting usage data: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Manage Bedrock API customers')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create customer command
    create_parser = subparsers.add_parser('create', help='Create a new customer')
    create_parser.add_argument('--name', required=True, help='Customer name')
    create_parser.add_argument('--email', required=True, help='Customer email')
    create_parser.add_argument('--token', help='Custom Bearer token (optional)')
    
    # List customers command
    subparsers.add_parser('list', help='List all customers')
    
    # Rotate token command
    rotate_parser = subparsers.add_parser('rotate-token', help='Rotate a customer\'s Bearer token')
    rotate_parser.add_argument('--customer-id', required=True, help='Customer ID')
    
    # Update limits command
    limits_parser = subparsers.add_parser('update-limits', help='Update a customer\'s usage limits')
    limits_parser.add_argument('--customer-id', required=True, help='Customer ID')
    limits_parser.add_argument('--daily-limit', required=True, type=int, help='Daily request limit')
    
    # Get usage command
    usage_parser = subparsers.add_parser('usage', help='Get customer usage')
    usage_parser.add_argument('--customer-id', required=True, help='Customer ID')
    usage_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    usage_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    manager = CustomerManager()
    
    if args.command == 'create':
        manager.create_customer(args.name, args.email, args.token)
    elif args.command == 'list':
        manager.list_customers()
    elif args.command == 'rotate-token':
        manager.rotate_token(args.customer_id)
    elif args.command == 'update-limits':
        manager.update_limits(args.customer_id, args.daily_limit)
    elif args.command == 'usage':
        manager.get_customer_usage(args.customer_id, args.start_date, args.end_date)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()