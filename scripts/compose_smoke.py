import json
import os
import time
import urllib.request
from uuid import uuid4


def read_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} respondeu HTTP {response.status}")
        return response.read().decode("utf-8")


def synthetic_pdf(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(content)


def create_document(url: str) -> dict[str, object]:
    boundary = f"qa-method-{uuid4().hex}"
    pdf = synthetic_pdf("Documento sintetico para smoke do worker persistente.")
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="smoke.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("ascii") + pdf + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise RuntimeError(f"A admissão respondeu HTTP {response.status}.")
        return json.loads(response.read())


def create_run(url: str, document_id: str, idempotency_key: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps({"document_id": document_id, "mode": "demo"}).encode(),
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 202:
            raise RuntimeError(f"A criação do run respondeu HTTP {response.status}.")
        return json.loads(response.read())


def search_document(url: str, document_id: str, query: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {"document_id": document_id, "query": query, "limit": 10}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"A busca respondeu HTTP {response.status}.")
        return json.loads(response.read())


api_url = os.environ["QA_API_URL"].rstrip("/")
web_url = os.environ["QA_WEB_URL"].rstrip("/")

health = json.loads(read_text(f"{api_url}/health"))
if health.get("status") != "ok":
    raise RuntimeError("O healthcheck da API não retornou status ok.")

proxied_health = json.loads(read_text(f"{web_url}/api/health"))
if proxied_health != health:
    raise RuntimeError("O proxy /api da interface não preservou a resposta do backend.")

capabilities = json.loads(read_text(f"{api_url}/capabilities"))
demo = next(item for item in capabilities["capabilities"] if item["mode"] == "demo")
if not demo["available"] or demo["provider"] != "local":
    raise RuntimeError("O modo demo offline não está disponível.")

documents = json.loads(read_text(f"{api_url}/api/v1/documents"))
if not isinstance(documents.get("documents"), list):
    raise RuntimeError("A API persistente de documentos não respondeu com uma lista.")

document = create_document(f"{api_url}/api/v1/documents")
pages = json.loads(read_text(f"{api_url}/api/v1/documents/{document['id']}/pages"))["pages"]
if len(pages) != 1 or pages[0].get("status") != "extracted":
    raise RuntimeError("A classificação persistida da página digital não foi reaberta.")
if pages[0].get("character_count", 0) < 1 or pages[0].get("has_images") is not False:
    raise RuntimeError("Os sinais de qualidade da página digital estão incorretos.")
search = search_document(
    f"{api_url}/api/v1/search", str(document["id"]), "worker persistente"
)
if search.get("retrieval_mode") != "lexical" or search.get("query") != "worker persistente":
    raise RuntimeError("A busca lexical não identificou modo e consulta corretamente.")
if len(search.get("hits", [])) != 1 or search["hits"][0].get("page") != 1:
    raise RuntimeError("A busca lexical não recuperou a unidade anotada.")
if "worker persistente" not in search["hits"][0].get("snippet", ""):
    raise RuntimeError("A busca lexical não preservou a evidência no trecho.")
idempotency_key = f"compose-smoke-{uuid4().hex}"
run = create_run(f"{api_url}/api/v1/runs", str(document["id"]), idempotency_key)
duplicate = create_run(f"{api_url}/api/v1/runs", str(document["id"]), idempotency_key)
if duplicate["id"] != run["id"]:
    raise RuntimeError("A submissão idempotente criou runs diferentes.")
runs = json.loads(read_text(f"{api_url}/api/v1/runs"))["runs"]
if not any(item["id"] == run["id"] for item in runs):
    raise RuntimeError("O run criado não apareceu no histórico persistente.")

for _ in range(40):
    run = json.loads(read_text(f"{api_url}/api/v1/runs/{run['id']}"))
    if run["status"] not in {"queued", "running"}:
        break
    time.sleep(0.25)
if run["status"] != "succeeded":
    raise RuntimeError(f"O worker encerrou o run com estado {run['status']}.")

result = json.loads(read_text(f"{api_url}/api/v1/runs/{run['id']}/result"))
if len(result["report"]["dimensions"]) != 6:
    raise RuntimeError("O resultado persistido não contém as seis dimensões.")

index = read_text(web_url)
if '<div id="root"></div>' not in index:
    raise RuntimeError("A interface não entregou o ponto de montagem React esperado.")

evaluation_route = read_text(f"{web_url}/evaluation")
if '<div id="root"></div>' not in evaluation_route:
    raise RuntimeError("O fallback de rotas da SPA não respondeu em /evaluation.")

search_route = read_text(f"{web_url}/search")
if '<div id="root"></div>' not in search_route:
    raise RuntimeError("O fallback de rotas da SPA não respondeu em /search.")

print("Smoke test dos contêineres concluído com sucesso.")
