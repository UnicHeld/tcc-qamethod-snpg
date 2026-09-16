import json
import os
import time
import urllib.error
import urllib.request
from uuid import uuid4


def synthetic_pdf(*page_texts: str) -> bytes:
    page_count = len(page_texts)
    page_object_ids = tuple(range(3, 3 + page_count))
    content_object_ids = tuple(range(3 + page_count, 3 + (2 * page_count)))
    font_object_id = 3 + (2 * page_count)
    kids = " ".join(f"{object_id} 0 R" for object_id in page_object_ids)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"),
    ]

    for content_object_id in content_object_ids:
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> "
                f"/Contents {content_object_id} 0 R >>"
            ).encode("ascii")
        )
    for text in page_texts:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, pdf_object in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(pdf_object)
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


def request_json(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: float = 30,
) -> dict[str, object]:
    headers = {"Content-Type": content_type} if content_type else {}
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} respondeu HTTP {error.code}: {body}") from error


def create_document(api_url: str) -> str:
    boundary = f"qa-method-vector-{uuid4().hex}"
    pdf = synthetic_pdf(
        "O estudo reuniu depoimentos por entrevistas semiestruturadas e analise tematica.",
        "O levantamento apresenta tabelas estatisticas, questionarios e percentuais numericos.",
    )
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="vector-smoke.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("ascii") + pdf + f"\r\n--{boundary}--\r\n".encode("ascii")
    document = request_json(
        f"{api_url}/api/v1/documents",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    return str(document["id"])


def search(api_url: str, document_id: str, query: str, mode: str) -> dict[str, object]:
    return request_json(
        f"{api_url}/api/v1/search",
        data=json.dumps(
            {
                "document_id": document_id,
                "query": query,
                "limit": 2,
                "retrieval_mode": mode,
            }
        ).encode("utf-8"),
        content_type="application/json",
        timeout=900,
    )


def first_page(result: dict[str, object]) -> int | None:
    hits = result.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    page = hits[0].get("page")
    return page if isinstance(page, int) else None


def main() -> None:
    api_url = os.environ.get("QA_API_URL", "http://127.0.0.1:18001").rstrip("/")
    capabilities = request_json(f"{api_url}/capabilities")
    vector_capability = next(
        item
        for item in capabilities["retrieval_capabilities"]
        if item["mode"] == "vector"
    )
    if not vector_capability["available"]:
        raise RuntimeError(f"A busca vetorial está indisponível: {vector_capability['reason']}")

    document_id = create_document(api_url)
    lexical = search(api_url, document_id, "entrevistas", "lexical")
    if first_page(lexical) != 1:
        raise RuntimeError("A busca lexical de controle não recuperou a página anotada.")

    semantic_query = "Como os participantes foram ouvidos para interpretar seus relatos?"
    started_at = time.monotonic()
    cold = search(api_url, document_id, semantic_query, "vector")
    cold_seconds = time.monotonic() - started_at
    started_at = time.monotonic()
    warm = search(api_url, document_id, semantic_query, "vector")
    warm_seconds = time.monotonic() - started_at

    if first_page(cold) != 1 or first_page(warm) != 1:
        raise RuntimeError("A busca vetorial não recuperou a página semântica anotada no top-1.")
    if cold.get("embedding_model") != vector_capability["model"]:
        raise RuntimeError("A resposta vetorial não identificou o modelo configurado.")
    if cold.get("embedding_dimension") != vector_capability["dimension"]:
        raise RuntimeError("A resposta vetorial não identificou a dimensão configurada.")
    if cold.get("chunk_version") is None:
        raise RuntimeError("A resposta vetorial não identificou a versão de chunk.")

    summary = {
        "document_id": document_id,
        "query": semantic_query,
        "annotated_relevant_page": 1,
        "lexical_control_top_page": first_page(lexical),
        "vector_cold_top_page": first_page(cold),
        "vector_warm_top_page": first_page(warm),
        "recall_at_1": 1.0,
        "cold_seconds": round(cold_seconds, 3),
        "warm_seconds": round(warm_seconds, 3),
        "embedding_model": cold["embedding_model"],
        "embedding_dimension": cold["embedding_dimension"],
        "chunk_version": cold["chunk_version"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
