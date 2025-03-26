#!/bin/bash
# Script to set up API Gateway for Bearer token authentication

# Create API
API_ID=$(aws apigateway create-rest-api \
  --name "Bedrock-Proxy-API" \
  --description "API for Bedrock Model Access" \
  --endpoint-configuration "{ \"types\": [\"REGIONAL\"] }" \
  --output text \
  --query "id")

echo "Created API with ID: $API_ID"

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --output text \
  --query "items[0].id")

# Create resource
RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part "bedrock" \
  --output text \
  --query "id")

echo "Created resource with ID: $RESOURCE_ID"

# Create POST method (no API key requirement)
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE

echo "Created POST method"

# Replace with your Lambda function ARN
LAMBDA_ARN="arn:aws:lambda:REGION:ACCOUNT_ID:function:bedrock-proxy"

# Set up Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"

echo "Set up Lambda integration"

# Set up method response
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --status-code 200 \
  --response-models '{"application/json": "Empty"}'

# Create OPTIONS method for CORS
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --authorization-type NONE

# Set up CORS integration response
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --type MOCK \
  --integration-http-method OPTIONS \
  --request-templates '{"application/json": "{\"statusCode\": 200}"}'

aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{
    "method.response.header.Access-Control-Allow-Headers": "'\''Content-Type,Authorization'\''"
  }' \
  --response-templates '{"application/json": ""}'

# Set up CORS method response
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-models '{"application/json": "Empty"}' \
  --response-parameters '{
    "method.response.header.Access-Control-Allow-Headers": true,
    "method.response.header.Access-Control-Allow-Methods": true,
    "method.response.header.Access-Control-Allow-Origin": true
  }'

# Create a deployment
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

echo "Created deployment to 'prod' stage"

echo "API Gateway setup complete! Use the following endpoint:"
echo "https://$API_ID.execute-api.REGION.amazonaws.com/prod/bedrock"
echo "Remember to provide Bearer tokens to your customers for authentication."