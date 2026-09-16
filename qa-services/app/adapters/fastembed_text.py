from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.search import EmbeddingProfile

if TYPE_CHECKING:
    from fastembed import TextEmbedding
    from tokenizers import Tokenizer


class FastEmbedTextEmbedder:
    def __init__(self, profile: EmbeddingProfile, cache_dir: str | None = None) -> None:
        self.profile = profile
        self.cache_dir = cache_dir

    @cached_property
    def _tokenizer(self) -> "Tokenizer":
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        tokenizer_cache = (
            str(Path(self.cache_dir) / "huggingface") if self.cache_dir else None
        )
        tokenizer_path = hf_hub_download(
            repo_id=self.profile.model,
            filename="tokenizer.json",
            cache_dir=tokenizer_cache,
        )
        return Tokenizer.from_file(str(Path(tokenizer_path)))

    @cached_property
    def _model(self) -> "TextEmbedding":
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType

        supported_models = {
            item["model"].casefold() for item in TextEmbedding.list_supported_models()
        }
        if self.profile.model.casefold() not in supported_models:
            TextEmbedding.add_custom_model(
                model=self.profile.model,
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf=self.profile.model),
                dim=self.profile.dimension,
                model_file="onnx/model_O4.onnx",
            )
        model_cache = str(Path(self.cache_dir) / "fastembed") if self.cache_dir else None
        return TextEmbedding(
            model_name=self.profile.model,
            cache_dir=model_cache,
            threads=1,
        )

    def chunk(self, text: str) -> tuple[str, ...]:
        token_ids = self._tokenizer.encode(text, add_special_tokens=False).ids
        if not token_ids:
            return ()

        chunks: list[str] = []
        step = self.profile.max_tokens - self.profile.overlap_tokens
        for start in range(0, len(token_ids), step):
            chunk_ids = token_ids[start : start + self.profile.max_tokens]
            chunk_text = self._tokenizer.decode(chunk_ids).strip()
            if chunk_text:
                chunks.append(chunk_text)
            if start + self.profile.max_tokens >= len(token_ids):
                break
        return tuple(chunks)

    def embed_passages(self, passages: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        prefixed = [f"passage: {passage}" for passage in passages]
        return tuple(
            tuple(float(value) for value in vector)
            for vector in self._model.embed(prefixed)
        )

    def embed_query(self, query: str) -> tuple[float, ...]:
        vector = next(iter(self._model.embed([f"query: {query}"])))
        return tuple(float(value) for value in vector)
