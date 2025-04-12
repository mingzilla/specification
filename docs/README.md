# Specification Repository

This repository hosts various technical specifications and documentation for reference and implementation guidance.

## Chat Completions API

The [Chat Completions API Specification](https://mingzilla.github.io/specification/streaming-api-spec) provides detailed guidelines for implementing a chat completions API that supports both regular invocations and streaming responses.

Key features:
- JSON and SSE streaming formats
- Request and response format examples
- Error handling guidelines
- Client and server implementation examples
- Strictly follows RPC (Remote Procedure Call) Specification, which is compatible with MCP (Model Context Protocol). Refer to https://spec.modelcontextprotocol.io for details

## MCP Workflow and Sampling

The [Understanding MCP Sampling](https://mingzilla.github.io/specification/mcp-sampling-guide) is almost like a missing doc from the MCP official site. This doc should well explain MCP Sampling, which DOES NOT mean "Sampling Data" at all!

MCP Sampling is to implement a sampleHandler callback function, which can be called by the MCP Server. Since the callback function is on the client side, the client side can call a LLM via HTTP REST requests, or you can ask a user to approve an action.


## Chat Completion Integration (Draft)

- [Flux - Reactor - Spring Web Flux](https://mingzilla.github.io/specification/spring-web-flux)
- [Flux - Reactor - Java Reactive Concurrency Guide](https://mingzilla.github.io/specification/java-reactive-concurrency-guide)
- [LlmClient - Draft Design Spec](https://mingzilla.github.io/specification/llm-client-spec-draft)
- [Redis Pub Sub With Reactor](draft/2025-04-12_redis-pub-sub/ai-copilot-redis-implementation-v2.md)


## AWS Bedrock Provider Implementation Solution (Draft)

- [AWS Bedrock Lambda Proxy](https://mingzilla.github.io/specification/draft/2025-03-26_bed-rock-proxy/bedrock-lambda-proxy)
- [AWS Bedrock Lambda Proxy - Customer Usage Tracking](https://mingzilla.github.io/specification/draft/2025-03-26_bed-rock-tracking/bedrock-usage-tracking)

## Observability

- [Component Diagnostics Utility Specification](https://mingzilla.github.io/specification/other/diagnostic-util-spec/diagnostic-util-spec)


## Cheat Sheet

- [Cheat Sheet - Java Stream API](https://mingzilla.github.io/specification/other/java-stream-api)
- [Cheat Sheet - Apache Lucene 9.8](https://mingzilla.github.io/specification/other/lucene-9.8-cheatsheet)

## Other

- [Confusing Terminologies](other/terminologies.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.