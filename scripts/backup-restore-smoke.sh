#!/usr/bin/env sh
set -eu

case "${COMPOSE_PROJECT_NAME:-}" in
    qa-method-test*) ;;
    *)
        echo "Este smoke só pode alterar um projeto Compose qa-method-test*." >&2
        exit 2
        ;;
esac

compose() {
    if [ -n "${QA_COMPOSE_ENV_FILE:-}" ]; then
        docker compose --env-file "$QA_COMPOSE_ENV_FILE" "$@"
    else
        docker compose "$@"
    fi
}

postgres_user="${QA_POSTGRES_USER:-qa_method}"
postgres_database="${QA_POSTGRES_DB:-qa_method}"
temporary_directory="$(mktemp -d -t qa-method-backup-smoke.XXXXXX)"
backup_path="$temporary_directory/postgres.dump"
interrupted_run_id="00000000-0000-4000-8000-000000000003"

cleanup() {
    rm -f "$backup_path"
    rmdir "$temporary_directory" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

document_count() {
    compose exec -T database psql \
        --username "$postgres_user" --dbname "$postgres_database" \
        --tuples-only --no-align --command "SELECT count(*) FROM documents"
}

count_before="$(document_count)"
if [ "$count_before" -lt 1 ]; then
    echo "O smoke precisa de ao menos um documento persistido." >&2
    exit 1
fi

"$(dirname "$0")/backup-postgres.sh" "$backup_path"
compose exec -T database psql \
    --username "$postgres_user" --dbname "$postgres_database" \
    --command "TRUNCATE TABLE documents CASCADE" >/dev/null
if [ "$(document_count)" -ne 0 ]; then
    echo "A preparação isolada do restore não removeu os documentos." >&2
    exit 1
fi

QA_RESTORE_CONFIRM=restore-local-database \
    "$(dirname "$0")/restore-postgres.sh" "$backup_path"
if [ "$(document_count)" -ne "$count_before" ]; then
    echo "O restore não recuperou a contagem original de documentos." >&2
    exit 1
fi

compose stop worker >/dev/null
compose exec -T database psql \
    --username "$postgres_user" --dbname "$postgres_database" \
    --command "
        INSERT INTO evaluation_runs (
            id, document_id, mode, provider, model, prompt_version, status, started_at
        )
        SELECT
            '$interrupted_run_id', id, 'demo', 'local', 'deterministic-demo-v1',
            'qa-method-structured-v2', 'running', now()
        FROM documents
        ORDER BY created_at
        LIMIT 1
    " >/dev/null
compose up --detach worker >/dev/null

status="running"
attempt=0
while [ "$status" = "running" ] && [ "$attempt" -lt 20 ]; do
    sleep 0.25
    status="$(
        compose exec -T database psql \
            --username "$postgres_user" --dbname "$postgres_database" \
            --tuples-only --no-align \
            --command "SELECT status FROM evaluation_runs WHERE id = '$interrupted_run_id'"
    )"
    attempt=$((attempt + 1))
done
if [ "$status" != "interrupted" ]; then
    echo "O worker reiniciado deixou o run no estado $status." >&2
    exit 1
fi

echo "Smoke de backup, restore e reinício do worker concluído com sucesso."
