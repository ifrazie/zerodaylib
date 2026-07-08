$ agentcore dev
Starting web UI...
Log: agentcore\.cli\logs\dev\dev-20260707-233355.log

---

## Qwen MCP tool-call incompatibility (`Unknown tool: <name><|channel|>commentary`)

**Status:** Open blocker for Layer 3 behavioral tests
**Discovered:** 2026-07-08 via `backend/tests/test_agent_behavior.py`
**Affects:** All three agents (zdl_supervisorAgent, zdl_ingestAgent, zdl_governanceAgent)

### Symptom

When an agent attempts to call an MCP gateway tool, the Strands executor logs:

```
tool_name=<zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update<|channel|>commentary> | invalid tool name pattern
```

The model then receives `"Unknown tool"` in the tool result, enters an infinite retry
loop, and exhausts its token budget with `MaxTokensReachedException`.

### Root Cause

The Qwen model (`qwen.qwen3-coder-30b-a3b-instruct`) served via Bedrock Mantle's
OpenAI-compatible endpoint uses a proprietary tool-call format. When generating a
function call, Qwen appends a `<|channel|>commentary` suffix to the tool name:

- **Expected by Strands registry:** `zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update`
- **Emitted by Qwen:** `zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update<|channel|>commentary`

Strands' `ToolExecutor` does an exact registry lookup on `tool_use["name"]` and returns
`"Unknown tool"` when the suffix-modified name is not found.

Note: renaming the gateway target from `zdl-tools` to `zdltools` (removing the hyphen)
was a separate fix that was also required — the hyphen caused a distinct Strands tool-dispatch
failure via `MCPAgentTool.prefixed_name`, and is now resolved.

### Resolution Options

1. **Switch to a standard OpenAI function-calling model** (e.g. `anthropic.claude-*`
   via the Bedrock Converse API). These emit standard function-call JSON without channel
   tokens. Requires updating `app/*/model/load.py` and `app/*/pyproject.toml`.

2. **Write a Strands model adapter** that post-processes the Qwen model's output to
   strip `<|channel|>commentary` from tool names before they reach the Strands
   dispatcher. Subclass `strands.models.openai.OpenAIModel` and override the stream
   / tool-result processing methods.

### Test Tracking

`backend/tests/test_agent_behavior.py` marks all three behavioral scenarios as
`@pytest.mark.xfail(strict=True)`. They run and fail as expected (CI green). They will
xpass automatically once the model or adapter issue is resolved.

---

Chat UI: http://localhost:8081
Press Ctrl+C to stop

Web UI: [zdl_supervisorAgent] {"timestamp": "2026-07-08T03:35:03.679Z", "level": "ERROR", "message": "Error in sync streaming", "logger": "bedrock_agentcore.app", "requestId": "4f48bf25-cc89-48ba-83fe-f9fe88978c68", "sessionId": "1944deab-cde3-45fb-b93b-8b9445a8172b", "errorType": "AuthenticationError", "errorMessage": "Error code: 401 - {'error': {'code': 'access_denied', 'message': 'Berm is not enabled for this account', 'param': None, 'type': 'permission_denied_error'}}", "stackTrace": ["Traceback (most recent call last):\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\bedrock_agentcore\\runtime\\app.py\", line 938, in _sync_stream_with_error_handling\n    for value in generator:\n                 ^^^^^^^^^\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\bedrock_agentcore\\runtime\\app.py\", line 786, in _async_gen_to_sync_gen\n    raise value\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\bedrock_agentcore\\runtime\\app.py\", line 745, in _produce\n    async for chunk in async_gen:\n    ...<2 lines>...\n            return\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\main.py\", line 247, in invoke\n    async for event in agent.stream_async(\n    ...<7 lines>...\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\agent\\agent.py\", line 1193, in stream_async\n    async for event in events:\n    ...<5 lines>...\n            yield as_dict\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\agent\\agent.py\", line 1280, in _run_loop\n    async for event in events:\n    ...<14 lines>...\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\agent\\agent.py\", line 1351, in _execute_event_loop_cycle\n    async for event in events:\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\event_loop.py\", line 295, in event_loop_cycle\n    async for model_event in model_events:\n        if not isinstance(model_event, ModelStopReason):\n            yield model_event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\event_loop.py\", line 621, in _handle_model_execution\n    raise e\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\event_loop.py\", line 542, in _handle_model_execution\n    async for event in agent._middleware_registry.invoke(\n    ...<7 lines>...\n            yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\_middleware\\registry.py\", line 140, in invoke\n    async for event in gen:\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\event_loop.py\", line 661, in terminal\n    async for event in stream_messages(\n    ...<10 lines>...\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\streaming.py\", line 514, in stream_messages\n    async for event in process_stream(chunks, start_time, cancel_signal):\n        yield event\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\event_loop\\streaming.py\", line 424, in process_stream\n    async for chunk in chunks:\n    ...<35 lines>...\n            handle_redact_content(chunk[\"redactContent\"], state)\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\strands\\models\\openai.py\", line 716, in stream\n    response = await client.chat.completions.create(**request)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\openai\\resources\\chat\\completions\\completions.py\", line 2814, in create\n    return await self._post(\n           ^^^^^^^^^^^^^^^^^\n    ...<54 lines>...\n    )\n    ^\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\openai\\_base_client.py\", line 1931, in post\n    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n", "  File \"D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\openai\\_base_client.py\", line 1716, in request\n    raise self._make_status_error_from_response(err.response) from None\n", "openai.AuthenticationError: Error code: 401 - {'error': {'code': 'access_denied', 'message': 'Berm is not enabled for this account', 'param': None, 'type': 'permission_denied_error'}}\n"], "location": "D:\\projects\\zerodaylib\\app\\zdl_supervisorAgent\\.venv\\Lib\\site-packages\\bedrock_agentcore\\runtime\\app.py:_sync_stream_with_error_handling:941"}
Web UI: [zdl_supervisorAgent] 2026-07-07 23:35:03,679 ERROR [bedrock_agentcore.app] [app.py:941] [trace_id=6a4dc5617ed849b49156365473d34044 span_id=dbd3b14956908c6f resource.service.name=zdl_supervisorAgent trace_sampled=True] - Error in sync streaming
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\bedrock_agentcore\runtime\app.py", line 938, in _sync_stream_with_error_handling
Web UI: [zdl_supervisorAgent]     for value in generator:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\bedrock_agentcore\runtime\app.py", line 786, in _async_gen_to_sync_gen
Web UI: [zdl_supervisorAgent]     raise value
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\bedrock_agentcore\runtime\app.py", line 745, in _produce
Web UI: [zdl_supervisorAgent]     async for chunk in async_gen:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\main.py", line 247, in invoke
Web UI: [zdl_supervisorAgent]     async for event in agent.stream_async(
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\agent\agent.py", line 1193, in stream_async
Web UI: [zdl_supervisorAgent]     async for event in events:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\agent\agent.py", line 1280, in _run_loop
Web UI: [zdl_supervisorAgent]     async for event in events:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\agent\agent.py", line 1351, in _execute_event_loop_cycle
Web UI: [zdl_supervisorAgent]     async for event in events:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\event_loop.py", line 295, in event_loop_cycle
Web UI: [zdl_supervisorAgent]     async for model_event in model_events:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\event_loop.py", line 621, in _handle_model_execution
Web UI: [zdl_supervisorAgent]     raise e
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\event_loop.py", line 542, in _handle_model_execution
Web UI: [zdl_supervisorAgent]     async for event in agent._middleware_registry.invoke(
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\_middleware\registry.py", line 140, in invoke
Web UI: [zdl_supervisorAgent]     async for event in gen:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\event_loop.py", line 661, in terminal
Web UI: [zdl_supervisorAgent]     async for event in stream_messages(
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\streaming.py", line 514, in stream_messages
Web UI: [zdl_supervisorAgent]     async for event in process_stream(chunks, start_time, cancel_signal):
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\event_loop\streaming.py", line 424, in process_stream
Web UI: [zdl_supervisorAgent]     async for chunk in chunks:
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\strands\models\openai.py", line 716, in stream
Web UI: [zdl_supervisorAgent]     response = await client.chat.completions.create(**request)
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\openai\resources\chat\completions\completions.py", line 2814, in create
Web UI: [zdl_supervisorAgent]     return await self._post(
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\openai\_base_client.py", line 1931, in post
Web UI: [zdl_supervisorAgent]     return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
Web UI: [zdl_supervisorAgent]   File "D:\projects\zerodaylib\app\zdl_supervisorAgent\.venv\Lib\site-packages\openai\_base_client.py", line 1716, in request
Web UI: [zdl_supervisorAgent]     raise self._make_status_error_from_response(err.response) from None
Web UI: [zdl_supervisorAgent] openai.AuthenticationError: Error code: 401 - {'error': {'code': 'access_denied', 'message': 'Berm is not enabled for this account', 'param': None, 'type': 'permission_denied_error'}}