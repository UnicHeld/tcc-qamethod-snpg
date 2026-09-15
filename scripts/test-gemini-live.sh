#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
project_name="${COMPOSE_PROJECT_NAME:-qa-method-live-smoke}"
api_port="${QA_LIVE_API_PORT:-18000}"
test_directory=$(mktemp -d -t qa-method-gemini-live.XXXXXX)
fixture_path="$test_directory/synthetic.pdf"
capabilities_path="$test_directory/capabilities.json"
response_path="$test_directory/response.json"
docker_config="$test_directory/docker-config"
current_stage="preparação"
mkdir -p "$docker_config"

compose() {
    QA_API_PORT="$api_port" \
        DOCKER_CONFIG="$docker_config" \
        docker compose \
        --env-file "$repository_root/.env" \
        --project-directory "$repository_root" \
        --project-name "$project_name" \
        "$@"
}

cleanup() {
    exit_status=$?
    if [ "$exit_status" -ne 0 ]; then
        echo "Diagnóstico sanitizado da API:" >&2
        compose logs --no-color api 2>/dev/null \
            | sed -n '/gemini_provider_error/p;/POST \/evaluation\/upload/p' >&2 \
            || true
    fi
    compose down --volumes --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$test_directory"
    if [ "$exit_status" -ne 0 ]; then
        echo "Smoke real interrompido na etapa: $current_stage." >&2
    fi
}

trap cleanup EXIT INT TERM

if [ ! -f "$repository_root/.env" ]; then
    echo "Crie .env na raiz com GEMINI_API_KEY antes do smoke real." >&2
    exit 1
fi

unset GEMINI_API_KEY GEMINI_FALLBACK_API_KEY GOOGLE_API_KEY

current_stage="leitura segura da configuração"
if ! compose config --format json \
    | jq --exit-status '
        .services.api.environment.GEMINI_API_KEY
        | type == "string" and length > 0
    ' >/dev/null; then
    echo "O Compose leu o .env, mas GEMINI_API_KEY continuou vazia." >&2
    echo "Salve o arquivo .env no editor antes de executar o smoke (a aba não pode exibir o indicador de alteração não salva)." >&2
    echo "Confirme uma linha no formato exato GEMINI_API_KEY=valor, sem prefixo VITE_." >&2
    exit 1
fi

echo "[1/4] Construindo o ambiente isolado..."
current_stage="construção dos contêineres"
compose --profile test build api backend-tests
current_stage="criação do PDF sintético"
compose --profile test run --rm --no-deps backend-tests \
    python -c 'from tests.pdf_factory import synthetic_pdf; import sys; sys.stdout.buffer.write(synthetic_pdf("Documento academico sintetico e autorizado para validar a integracao Gemini."))' \
    > "$fixture_path"
echo "[2/4] Iniciando PostgreSQL e API..."
current_stage="inicialização da stack"
compose up --detach --wait api

echo "[3/4] Conferindo a disponibilidade do modo real..."
current_stage="verificação de /capabilities"
curl --silent --show-error --fail "http://127.0.0.1:$api_port/capabilities" \
    --output "$capabilities_path"
if ! jq --exit-status '
        .capabilities[]
        | select(.mode == "real")
        | .available == true
    ' "$capabilities_path" >/dev/null; then
    jq --raw-output '
        .capabilities[]
        | select(.mode == "real")
        | "Modo real indisponível: \(.reason // "motivo não informado")"
    ' "$capabilities_path" >&2
    exit 1
fi

echo "[4/4] Enviando o PDF sintético ao Gemini; esta etapa pode levar até 180 segundos..."
current_stage="chamada ao Gemini"
if ! http_status=$(curl --silent --show-error \
        --max-time 200 \
        --write-out '%{http_code}' \
        --output "$response_path" \
        --form "file=@$fixture_path;type=application/pdf" \
        --form 'mode=real' \
        --form 'confirm_external_processing=true' \
        "http://127.0.0.1:$api_port/evaluation/upload"); then
    echo "A chamada HTTP ao backend falhou ou excedeu 200 segundos." >&2
    exit 1
fi

if [ "$http_status" != "200" ]; then
    jq '{http_status: $status, error: .detail}' --arg status "$http_status" "$response_path"
    exit 1
fi

current_stage="validação da resposta"
if ! jq --exit-status '
        .mode == "real"
        and .simulated == false
        and .provider == "google-gemini"
        and (.usage.credential_slot == "primary" or .usage.credential_slot == "fallback")
        and (.report.dimensions | length == 6)
        and ([paths | map(tostring) | join(".") | test("api_?key"; "i")] | any | not)
    ' "$response_path" >/dev/null; then
    echo "O backend respondeu HTTP 200, mas o contrato do smoke não foi atendido." >&2
    exit 1
fi

jq '{
    mode,
    simulated,
    provider,
    model,
    credential_slot: .usage.credential_slot,
    usage_kind: .usage.kind,
    input_tokens: .usage.input_tokens,
    output_tokens: .usage.output_tokens,
    dimensions: (.report.dimensions | length)
}' "$response_path"
echo "Smoke real do Gemini concluído com sucesso."
