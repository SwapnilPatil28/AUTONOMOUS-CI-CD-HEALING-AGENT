# Sandbox Execution

## Purpose

The backend executes repository tests using Docker when available, so untrusted project code runs inside a containerized workspace instead of directly on host by default.

## Current implementation

### Components

- `backend/app/services/test_engine.py`
  - `TestEngineService(use_docker=True)` is used by `RunnerService`.
  - Detects project test command (`pytest`, `npm test`, `mvn test`, `gradle test`, `dotnet test`).
- `backend/app/services/docker_executor.py`
  - Creates container, executes command, and performs cleanup.

### Runtime behavior

1. Runner requests a test execution.
2. Test engine checks Docker availability (`docker version`).
3. If available:
   - Creates container from `python:3.12-slim`.
   - Mounts target repository at `/workspace`.
   - Runs command via `docker exec`.
   - Stops/removes container.
4. If Docker is not available:
   - Falls back to direct host execution.

## Notes and limitations

- Containerized execution isolates processes and filesystem scope to mounted workspace.
- Network behavior is Docker-default unless further daemon/config policy is applied.
- The current implementation does not set explicit CPU/memory quotas.

## Verifying Docker mode

Check Docker availability:

```bash
docker version
```

If available, run creation logs will include normal Docker lifecycle behavior and cleanup at run end.

## Related files

- `backend/app/services/test_engine.py`
- `backend/app/services/docker_executor.py`
- `backend/app/services/runner.py`
