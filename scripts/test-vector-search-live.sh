#!/usr/bin/env sh
set -eu

if [ "${QA_VECTOR_TEST_CONFIRM:-}" != "download-local-model" ]; then
    echo "Defina QA_VECTOR_TEST_CONFIRM=download-local-model para autorizar o download do modelo local." >&2
    exit 2
fi

project_name="${COMPOSE_PROJECT_NAME:-qa-method-vector-test}"
api_port="${QA_VECTOR_API_PORT:-18001}"
docker_config="${QA_DOCKER_CONFIG:-/tmp/qa-method-vector-docker-config}"
mkdir -p "$docker_config"

compose() {
    GEMINI_API_KEY= GEMINI_FALLBACK_API_KEY= GOOGLE_API_KEY= \
        QA_API_PORT="$api_port" \
        DOCKER_CONFIG="$docker_config" \
        docker compose --env-file /dev/null \
        --project-name "$project_name" \
        -f compose.yaml -f compose.vector.yaml "$@"
}

cleanup() {
    compose down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM

compose up --build --detach --wait api
QA_API_URL="http://127.0.0.1:$api_port" python3 scripts/vector_search_smoke.py
