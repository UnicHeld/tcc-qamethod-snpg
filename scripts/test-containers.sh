#!/usr/bin/env sh
set -eu

project_name="${COMPOSE_PROJECT_NAME:-qa-method-test}"
docker_config="${QA_DOCKER_CONFIG:-/tmp/qa-method-docker-config}"
mkdir -p "$docker_config"

compose() {
    GEMINI_API_KEY= GEMINI_FALLBACK_API_KEY= GOOGLE_API_KEY= \
        DOCKER_CONFIG="$docker_config" \
        docker compose --env-file /dev/null --project-name "$project_name" "$@"
}

cleanup() {
    compose down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM

compose config --quiet
compose --profile test build api web worker backend-tests frontend-tests
compose --profile test run --rm backend-tests
compose --profile test run --rm frontend-tests
compose up --detach --wait api web worker
compose --profile test run --rm --no-deps smoke-tests
COMPOSE_PROJECT_NAME="$project_name" \
    DOCKER_CONFIG="$docker_config" \
    QA_COMPOSE_ENV_FILE=/dev/null \
    ./scripts/backup-restore-smoke.sh
