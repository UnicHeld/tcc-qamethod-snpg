#!/usr/bin/env sh
set -eu

confirmation_phrase="restore-local-database"
if [ "$#" -ne 1 ]; then
    echo "Uso: QA_RESTORE_CONFIRM=$confirmation_phrase $0 CAMINHO_DO_BACKUP" >&2
    exit 2
fi

backup_path="$1"
postgres_user="${QA_POSTGRES_USER:-qa_method}"
postgres_database="${QA_POSTGRES_DB:-qa_method}"

if [ ! -f "$backup_path" ] || [ ! -r "$backup_path" ]; then
    echo "O backup não existe ou não pode ser lido: $backup_path" >&2
    exit 2
fi
if [ "${QA_RESTORE_CONFIRM:-}" != "$confirmation_phrase" ]; then
    echo "Restore cancelado: defina QA_RESTORE_CONFIRM=$confirmation_phrase." >&2
    exit 2
fi

compose() {
    if [ -n "${QA_COMPOSE_ENV_FILE:-}" ]; then
        docker compose --env-file "$QA_COMPOSE_ENV_FILE" "$@"
    else
        docker compose "$@"
    fi
}

restart_services() {
    compose up --detach api worker >/dev/null 2>&1 || true
}
trap restart_services EXIT INT TERM

compose up --detach --wait database
compose stop api worker
compose exec -T database \
    pg_restore --username "$postgres_user" --dbname "$postgres_database" \
    --clean --if-exists --no-owner --no-privileges --single-transaction --exit-on-error \
    < "$backup_path"
compose up --detach --wait api worker

trap - EXIT INT TERM
echo "Backup PostgreSQL restaurado de $backup_path"
