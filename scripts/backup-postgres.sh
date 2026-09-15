#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "Uso: $0 CAMINHO_DO_BACKUP" >&2
    exit 2
fi

backup_path="$1"
backup_directory="$(dirname -- "$backup_path")"
postgres_user="${QA_POSTGRES_USER:-qa_method}"
postgres_database="${QA_POSTGRES_DB:-qa_method}"

if [ ! -d "$backup_directory" ]; then
    echo "O diretório de destino não existe: $backup_directory" >&2
    exit 2
fi
if [ -e "$backup_path" ] && [ "${QA_BACKUP_OVERWRITE:-}" != "1" ]; then
    echo "O backup já existe. Use QA_BACKUP_OVERWRITE=1 para substituí-lo." >&2
    exit 2
fi

compose() {
    if [ -n "${QA_COMPOSE_ENV_FILE:-}" ]; then
        docker compose --env-file "$QA_COMPOSE_ENV_FILE" "$@"
    else
        docker compose "$@"
    fi
}

temporary_path="$(mktemp "${backup_path}.tmp.XXXXXX")"
cleanup() {
    if [ -f "$temporary_path" ]; then
        rm -f "$temporary_path"
    fi
}
trap cleanup EXIT INT TERM

compose exec -T database \
    pg_dump --username "$postgres_user" --dbname "$postgres_database" --format custom \
    > "$temporary_path"
chmod 600 "$temporary_path"
mv -f "$temporary_path" "$backup_path"
trap - EXIT INT TERM

echo "Backup PostgreSQL criado em $backup_path"
