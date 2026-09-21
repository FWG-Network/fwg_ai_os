#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEEP=0
[[ "${1:-}" == "--deep" ]] && DEEP=1

REPORT_DIR="$ROOT/.devcontainer/diagnostics"
REPORT="$REPORT_DIR/latest.txt"
mkdir -p "$REPORT_DIR"

START_TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"

PASS=0
WARN=0
FAIL=0
declare -a ISSUES=()

pass() {
  PASS=$((PASS + 1))
  printf '[PASS] %s\n' "$1"
}

warn() {
  WARN=$((WARN + 1))
  printf '[WARN] %s\n' "$1"
  [[ -n "${2:-}" ]] && printf '       %s\n' "$2"
  ISSUES+=("WARN|$1|${2:-}")
}

fail() {
  FAIL=$((FAIL + 1))
  printf '[FAIL] %s\n' "$1"
  [[ -n "${2:-}" ]] && printf '       %s\n' "$2"
  ISSUES+=("FAIL|$1|${2:-}")
}

section() {
  printf '\n%s\n' "$1"
}

run_quiet() {
  "$@" >/dev/null 2>&1
}

echo "============================================================"
echo " FWG-AI-OS SMART DOCTOR v2"
echo " Started: $START_TS"
echo " Root:    $ROOT"
echo "============================================================"

section "DOCKER"

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker CLI unavailable" "Install/enable Docker before continuing."
else
  pass "Docker CLI available"

  if docker info >/dev/null 2>&1; then
    pass "Docker daemon reachable"
  else
    fail "Docker daemon unavailable" "Start/restart the Docker daemon."
  fi
fi

section "COMPOSE"

if docker compose config -q >/dev/null 2>&1; then
  pass "Docker Compose configuration valid"
else
  fail "Docker Compose configuration invalid" \
       "Run: docker compose config"
fi

section "CONTAINER RUNTIME"

for svc in db redis qdrant api worker; do
  state="$(docker compose ps --status running --services 2>/dev/null | grep -Fx "$svc" || true)"

  if [[ "$state" == "$svc" ]]; then
    pass "$svc container running"
  else
    fail "$svc container not running" \
         "Run: docker compose up -d $svc"
  fi
done

section "POSTGRESQL"

if docker compose exec -T api python - <<'PY' >/dev/null 2>&1
from sqlalchemy import create_engine, text
from backend.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

with engine.connect() as conn:
    row = conn.execute(
        text("SELECT current_user, current_database(), 1 AS probe")
    ).one()

assert row.probe == 1
assert row.current_user == "viral"
assert row.current_database == "viral"

engine.dispose()
PY
then
  pass "PostgreSQL application connection"
  printf '       authenticated as viral / database viral\n'
else
  fail "PostgreSQL application connection failed" \
       "Verify PostgreSQL, DATABASE_URL, and application credentials."
fi

section "REDIS"

REDIS_RESULT="$(
  docker compose exec -T redis redis-cli ping 2>/dev/null |
    tr -d '\r' |
    tail -1 || true
)"

if [[ "$REDIS_RESULT" == "PONG" ]]; then
  pass "Redis responding PONG"
else
  fail "Redis probe failed" \
       "Expected PONG; check Redis container and connectivity."
fi

section "QDRANT"

QDRANT_RESULT="$(
  docker compose exec -T api python - <<'PY' 2>/dev/null
import requests

base = "http://qdrant:6333"

r = requests.get(f"{base}/collections", timeout=5)
r.raise_for_status()

collections = r.json().get("result", {}).get("collections", [])
names = [x.get("name") for x in collections]

if "fwg_content" not in names:
    print("MISSING_COLLECTION")
    raise SystemExit(2)

info = requests.get(
    f"{base}/collections/fwg_content",
    timeout=5,
)
info.raise_for_status()

result = info.json().get("result", {})
status = result.get("status")
points = result.get("points_count")

print(f"status={status}")
print(f"points={points}")
PY
)"

if [[ "$QDRANT_RESULT" == *"status=green"* ]]; then
  pass "Qdrant fwg_content collection healthy"

  if [[ "$QDRANT_RESULT" == *"points=0"* ]]; then
    pass "Qdrant knowledge index ready for ingestion" \
         "fwg_content exists and is healthy; no content has been indexed yet."
  else
    pass "Qdrant fwg_content contains indexed points"
  fi
elif [[ "$QDRANT_RESULT" == *"MISSING_COLLECTION"* ]]; then
  pass "Qdrant fwg_content collection not initialized yet" \
       "Collection is created lazily by the canonical VectorMemory path on the first real memory operation."
else
  fail "Qdrant application probe failed" \
       "Expected reachable fwg_content collection with status=green."
fi

section "API"

API_STATUS="$(
  curl -fsS --max-time 5 \
    http://localhost:8000/os/status 2>/dev/null || true
)"

if [[ -n "$API_STATUS" ]]; then
  pass "API :8000 responding"

  if printf '%s' "$API_STATUS" | grep -q '"status":"operational"'; then
    pass "AIOS status = operational"
  else
    warn "API responded but AIOS is not operational" \
         "Inspect /os/status for dependency state."
  fi

  printf '%s\n' "$API_STATUS" | head -c 1200
  printf '\n'
else
  fail "API :8000 not responding" \
       "Run: docker compose logs --tail=100 api"
fi

section "CELERY WORKER"

WORKER_RESULT="$(
  docker compose exec -T worker python - <<'PY' 2>/dev/null
from backend.worker import celery_app

replies = celery_app.control.inspect(timeout=3).ping()

if not replies:
    raise SystemExit(2)

print("worker_ping=PASS")
print("workers=" + ",".join(sorted(replies.keys())))

registered = celery_app.control.inspect(timeout=3).registered() or {}

tasks = sorted(
    name
    for names in registered.values()
    for name in (names or [])
    if not name.startswith("celery.")
)

print("registered_tasks=" + str(len(tasks)))
print("registered_task_names=" + ",".join(tasks))
PY
)"

if [[ "$WORKER_RESULT" == *"worker_ping=PASS"* ]]; then
  pass "Celery live worker ping"

  WORKER_COUNT="$(printf '%s\n' "$WORKER_RESULT" |
    sed -n 's/^workers=//p' | head -1)"

  [[ -n "$WORKER_COUNT" ]] &&
    printf '       worker(s): %s\n' "$WORKER_COUNT"

  TASK_COUNT="$(printf '%s\n' "$WORKER_RESULT" |
    sed -n 's/^registered_tasks=//p' | head -1)"

  if [[ "$TASK_COUNT" == "0" ]]; then
    warn "Celery app has 0 registered application tasks" \
         "Worker is alive; no Celery task definitions were registered."
  else
    pass "Celery application tasks registered: $TASK_COUNT"
  fi
else
  fail "Celery worker did not respond to ping" \
       "Check worker logs and Redis broker connectivity."
fi

section "LLM CONFIGURATION"

LLM_VARS=(
  MODEL_REASONING
  MODEL_WRITER
  MODEL_FAST
  MODEL_CODER
)

for var in "${LLM_VARS[@]}"; do
  value="$(
    docker compose exec -T api python -c \
      "import os; print(os.getenv('$var',''))" 2>/dev/null |
      tail -1
  )"

  if [[ -n "$value" ]]; then
    pass "$var configured: $value"
  else
    fail "$var missing" \
         "Configure the model environment variable."
  fi
done

section "OPENROUTER"

OPENROUTER_RESULT="$(
  docker compose exec -T api python - <<'PY' 2>/dev/null
import os
import requests

key = os.getenv("OPENROUTER_API_KEY", "")
if not key:
    raise SystemExit(2)

r = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {key}"},
    timeout=10,
)

r.raise_for_status()

models = r.json().get("data", [])
free_models = {
    str(item.get("id"))
    for item in models
    if ":free" in str(item.get("id"))
}

print("reachable=PASS")
print("free_models=" + str(len(free_models)))

for env_name in (
    "MODEL_REASONING",
    "MODEL_WRITER",
    "MODEL_FAST",
    "MODEL_CODER",
):
    requested = os.getenv(env_name, "")
    if requested:
        print(
            env_name + "=" +
            ("AVAILABLE" if requested in free_models else "NOT_IN_CURRENT_FREE_LIST")
        )
PY
)"

if [[ "$OPENROUTER_RESULT" == *"reachable=PASS"* ]]; then
  pass "OpenRouter API reachable"

  while IFS='=' read -r name value; do
    case "$name" in
      MODEL_REASONING|MODEL_WRITER|MODEL_FAST|MODEL_CODER)
        if [[ "$value" == "AVAILABLE" ]]; then
          pass "$name model currently listed by OpenRouter"
        elif [[ "$value" == "NOT_IN_CURRENT_FREE_LIST" ]]; then
          warn "$name model not in current free-model list" \
               "Router may use its configured fallback."
        fi
        ;;
    esac
  done <<< "$OPENROUTER_RESULT"
else
  fail "OpenRouter API probe failed" \
       "Check OPENROUTER_API_KEY and outbound network access."
fi

section "RECENT LOG ERRORS"

# Only inspect fresh logs. Old historical errors should not degrade
# every terminal startup forever.
LOG_SINCE="10m"
ERROR_FOUND=0

for svc in db redis qdrant api worker; do
  logs="$(
    docker compose logs --since "$LOG_SINCE" --no-color "$svc" 2>/dev/null |
      grep -Ei '(^|[^a-z])(ERROR|FATAL|CRITICAL|Traceback|panic)([^a-z]|$)' |
      tail -5 || true
  )"

  if [[ -n "$logs" ]]; then
    case "$svc" in
      qdrant)
        # Qdrant telemetry/network reporting can fail while the local
        # Qdrant service remains healthy. Keep this informational.
        if printf '%s\n' "$logs" |
             grep -qi 'telemetry'; then
          warn "qdrant has recent telemetry/network warnings" \
               "Local Qdrant health is checked separately; telemetry failure is non-core."
        else
          warn "$svc has recent error-like log entries" \
               "$(printf '%s' "$logs" | tail -1)"
        fi
        ;;
      *)
        warn "$svc has recent error-like log entries" \
             "$(printf '%s' "$logs" | tail -1)"
        ;;
    esac
    ERROR_FOUND=1
  fi
done

if [[ "$ERROR_FOUND" -eq 0 ]]; then
  pass "No recent error-like log entries in core services"
fi

section "DEEP REAL E2E"

if [[ "$DEEP" -eq 1 ]]; then
  echo "Running real Task -> Executor -> DB -> LLM verification..."

  DEEP_RESULT="$(
    docker compose exec -T api python - <<'PY' 2>&1
import asyncio
import json

from sqlalchemy import select

from backend.models.db import SessionLocal, Task
from backend.aios.autonomous_loop import autonomous_loop_service

GOAL = "Reply with exactly: FWG_DOCTOR_DEEP_E2E_OK"

async def main():
    with SessionLocal() as db:
        result = await autonomous_loop_service.run(
            goal_description=GOAL,
            user_id="fwg-doctor",
            db=db,
        )

        goal_id = result.id
        if goal_id is None:
            raise RuntimeError("No goal_id returned")

        task = db.execute(
            select(Task)
            .where(Task.goal_id == goal_id)
            .order_by(Task.id.desc())
        ).scalars().first()

        if task is None:
            raise RuntimeError("No persisted task found")

        print("goal_id=", goal_id)
        print("goal_status=", result.status)
        print("task_id=", task.id)
        print("tool=", task.tool_name)
        print("status=", task.status)
        print("result=", json.dumps(task.result, default=str))

        if task.status != "completed":
            raise RuntimeError("Task did not complete")

        result_data = task.result or {}

        if result_data.get("response") != "FWG_DOCTOR_DEEP_E2E_OK":
            raise RuntimeError("Unexpected LLM response")

        if not result_data.get("model"):
            raise RuntimeError("Missing model provenance")

    print("DEEP_E2E=PASS")

asyncio.run(main())
PY
  )"

  if [[ "$DEEP_RESULT" == *"DEEP_E2E=PASS"* ]]; then
    pass "Real Task -> Executor -> DB -> LLM E2E"
    printf '%s\n' "$DEEP_RESULT" | tail -12
  else
    fail "Real deep E2E failed" \
         "Inspect the diagnostic output below."
    printf '%s\n' "$DEEP_RESULT" | tail -30
  fi
else
  echo "[SKIP] Deep E2E not requested."
  echo "       Run: .devcontainer/fwg-doctor.sh --deep"
fi

section "FINAL DIAGNOSIS"

if [[ "$FAIL" -gt 0 ]]; then
  STATUS="FAILED"
  ICON="🔴"
  SUMMARY="Core system is not ready."
elif [[ "$WARN" -gt 0 ]]; then
  STATUS="DEGRADED"
  ICON="🟡"
  SUMMARY="Core system is running, but warnings require attention."
else
  STATUS="HEALTHY"
  ICON="🟢"
  SUMMARY="All automatic core health checks passed."
fi

printf '%s %s\n' "$ICON" "FWG-AI-OS $STATUS"
printf 'PASS : %d\n' "$PASS"
printf 'WARN : %d\n' "$WARN"
printf 'FAIL : %d\n' "$FAIL"
printf 'RESULT: %s\n' "$STATUS"
printf '%s\n' "$SUMMARY"

if [[ "${#ISSUES[@]}" -gt 0 ]]; then
  echo
  echo "PRIMARY ISSUES"

  i=0
  for issue in "${ISSUES[@]}"; do
    i=$((i + 1))
    IFS='|' read -r level title reason <<< "$issue"

    printf '%d. [%s] %s\n' "$i" "$level" "$title"
    [[ -n "$reason" ]] && printf '   Reason: %s\n' "$reason"

    if [[ "$i" -ge 5 ]]; then
      break
    fi
  done

  echo
  echo "NEXT ACTION"
  if [[ "$FAIL" -gt 0 ]]; then
    echo "  Fix the first FAIL above, then rerun:"
    echo "    .devcontainer/fwg-doctor.sh"
  else
    echo "  Review WARN items above. Core runtime is still available."
  fi
fi

{
  echo "FWG-AI-OS SMART DOCTOR v2"
  echo "Started: $START_TS"
  echo "Result: $STATUS"
  echo "PASS=$PASS WARN=$WARN FAIL=$FAIL"
  echo
  echo "The full diagnostic output is intentionally generated"
  echo "by the command above and stored here:"
  echo "$REPORT"
} > "$REPORT"

chmod +x .devcontainer/fwg-doctor.sh

echo
echo "Diagnostic report: $REPORT"
echo "============================================================"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi

exit 0
