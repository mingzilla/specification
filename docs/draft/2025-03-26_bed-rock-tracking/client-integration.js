// Bedrock API Client Class
class BedrockClient {
  constructor(config) {
    this.apiEndpoint = config.apiEndpoint;
    this.apiKey = config.apiKey;
    this.defaultModel = config.defaultModel || 'anthropic.claude-3-sonnet-20240229-v1:0';
  }

  /**
   * Call a Bedrock model through the proxy
   * @param {Object} params - Request parameters
   * @param {string} [params.modelId] - Override default model
   * @param {Array} params.messages - Conversation messages
   * @param {number} [params.maxTokens] - Maximum tokens to generate
   * @param {number} [params.temperature] - Temperature for generation
   * @returns {Promise<Object>} - Model response
   */
  async callModel(params) {
    const modelId = params.modelId || this.defaultModel;
    
    // Determine payload structure based on model type
    let payload;
    
    if (modelId.includes('anthropic')) {
      // Claude model payload
      payload = {
        modelId: modelId,
        anthropic_version: 'bedrock-2023-05-31',
        max_tokens: params.maxTokens || 1000,
        temperature: params.temperature || 0.7,
        messages: params.messages
      };
    } else if (modelId.includes('meta')) {
      // Llama model payload
      payload = {
        modelId: modelId,
        max_gen_len: params.maxTokens || 512,
        temperature: params.temperature || 0.7,
        prompt: this._formatMessagesForLlama(params.messages)
      };
    } else {
      // Generic payload for other models
      payload = {
        modelId: modelId,
        ...params
      };
    }
    
    try {
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.apiKey
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${errorText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error calling Bedrock API:', error);
      throw error;
    }
  }
  
  /**
   * Format chat messages for Llama models
   * @private
   */
  _formatMessagesForLlama(messages) {
    return messages.map(msg => {
      const role = msg.role === 'user' ? 'Human' : 'Assistant';
      const content = Array.isArray(msg.content) 
        ? msg.content.map(c => c.text).join('\n')
        : msg.content;
      return `${role}: ${content}`;
    }).join('\n');
  }
}

// Example usage
async function demonstrateUsage() {
  const client = new BedrockClient({
    apiEndpoint: 'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/bedrock',
    apiKey: 'YOUR_API_KEY',
    defaultModel: 'anthropic.claude-3-sonnet-20240229-v1:0'
  });
  
  try {
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
    
    console.log('Model response:', response);
    
    // For Claude models, the content is in response.content
    if (response.content) {
      console.log('Answer:', response.content[0].text);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the example (in a browser environment, you'd call this differently)
// demonstrateUsage();

// Export for Node.js environments
if (typeof module !== 'undefined') {
  module.exports = { BedrockClient };
}
