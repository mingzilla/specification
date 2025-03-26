#!/bin/bash
# Script to set up API Gateway with Usage Plans

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

# Create POST method with API key required
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE \
  --api-key-required true

echo "Created POST method with API key requirement"

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

# Create a deployment
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

echo "Created deployment to 'prod' stage"

# Create a usage plan
USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
  --name "Bedrock-Standard-Plan" \
  --description "Standard usage plan for Bedrock API" \
  --throttle "rateLimit=10, burstLimit=20" \
  --quota "limit=1000, period=MONTH" \
  --output text \
  --query "id")

echo "Created usage plan with ID: $USAGE_PLAN_ID"

# Add stage to usage plan
aws apigateway update-usage-plan \
  --usage-plan-id $USAGE_PLAN_ID \
  --patch-operations "op=add,path=/apiStages,value=$API_ID:prod"

echo "Added 'prod' stage to usage plan"

echo "API Gateway setup complete! Use the following endpoint:"
echo "https://$API_ID.execute-api.REGION.amazonaws.com/prod/bedrock"
echo "Remember to create API keys for each customer and associate them with the usage plan."
