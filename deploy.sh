#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

log() {
  printf '\n[ai-teacher] %s\n' "$1"
}

fail() {
  printf '\n[ai-teacher] ERROR: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is not installed. Install Docker Engine/Desktop first."
docker info >/dev/null 2>&1 || fail "Docker daemon is not running or current user cannot access it."

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  fail "Docker Compose is not available."
fi

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    log "Created .env from .env.example"
  else
    touch .env
    log "Created empty .env"
  fi
fi

mkdir -p data data/uploads data/worksheets

PORT=$(awk -F= '/^AI_TEACHER_PORT=/{print $2}' .env | tail -n 1 | tr -d '[:space:]' || true)
PORT=${PORT:-8000}

log "Validating Docker Compose configuration"
$COMPOSE config >/dev/null

log "Building image"
$COMPOSE build --pull

log "Starting service"
$COMPOSE up -d --remove-orphans

log "Waiting for container health"
ATTEMPT=0
MAX_ATTEMPTS=40
while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; do
  STATUS=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ai-teacher 2>/dev/null || true)
  case "$STATUS" in
    healthy|running)
      break
      ;;
    unhealthy|exited|dead)
      $COMPOSE logs --tail=120 ai-teacher || true
      fail "Container entered state: $STATUS"
      ;;
  esac
  ATTEMPT=$((ATTEMPT + 1))
  sleep 2
done

STATUS=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ai-teacher 2>/dev/null || true)
[ "$STATUS" = "healthy" ] || [ "$STATUS" = "running" ] || {
  $COMPOSE logs --tail=120 ai-teacher || true
  fail "Service did not become ready. Current state: ${STATUS:-unknown}"
}

log "Deployment complete"
printf 'Service: http://127.0.0.1:%s\n' "$PORT"
printf 'Status : %s\n' "$STATUS"
printf 'Logs   : %s logs -f ai-teacher\n' "$COMPOSE"
printf 'Stop   : %s down\n' "$COMPOSE"
