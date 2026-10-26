"""Embed scripture verses after centering each book's embedding space.

The expected scripture layout is::

    root/
      work/
        book/
          chapter.txt

Each non-empty line in a chapter file becomes one document. The line number is
stored as the verse number.

Install dependencies with::

    pip install openai chromadb fire
"""

from __future__ import annotations

import json
import math
from functools import wraps
from pathlib import Path
from typing import Any, Iterable

import chromadb
from openai import OpenAI


MEAN_FILENAME = "embedding_mean.json"
DEFAULT_MODEL = "text-embedding-3-small"


def iter_documents(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    """Yield each non-empty line and its scripture metadata."""
    for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = file_path.relative_to(root)
        parts = relative.parts
        if len(parts) < 3:
            continue

        work, book = parts[0], parts[1]
        chapter = file_path.stem
        for line_number, line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            content = line.strip()
            if not content:
                continue

            yield content, {
                "work": work,
                "book": book,
                "chapter": chapter,
                "verse": line_number,
                "file_path": str(file_path),
                "content": content,
            }


def batches(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def embed_all(
        client: OpenAI,
        documents: list[str],
        model: str,
        batch_size: int,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for batch in batches(documents, batch_size):
        response = client.embeddings.create(model=model, input=batch)
        data = sorted(response.data, key=lambda item: item.index)
        embeddings.extend(item.embedding for item in data)
    return embeddings


def book_key(metadata: dict[str, Any]) -> str:
    return f"{metadata['work']}::{metadata['book']}"


def centered_unit_vectors_by_book(
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
) -> tuple[list[list[float]], dict[str, list[float]]]:
    """Center and normalize embeddings independently for each book."""
    if not embeddings:
        raise ValueError("No documents were found")

    grouped: dict[str, list[int]] = {}
    for index, metadata in enumerate(metadatas):
        grouped.setdefault(book_key(metadata), []).append(index)

    normalized: list[list[float] | None] = [None] * len(embeddings)
    means: dict[str, list[float]] = {}
    dimensions = len(embeddings[0])

    for key, indices in grouped.items():
        mean = [
            sum(embeddings[index][dimension] for index in indices) / len(indices)
            for dimension in range(dimensions)
        ]
        means[key] = mean

        for index in indices:
            centered = [
                value - mean_value
                for value, mean_value in zip(embeddings[index], mean)
            ]
            norm = math.sqrt(sum(value * value for value in centered))
            if norm == 0:
                raise ValueError(
                    f"An embedding has zero length after mean subtraction in {key}"
                )
            normalized[index] = [value / norm for value in centered]

    return [vector for vector in normalized if vector is not None], means


def ingest_folder(
        persist_dir: str,
        chroma_collection_name: str,
        folder: str,
        openai_model: str = DEFAULT_MODEL,
        batch_size: int = 256,
) -> None:
    """Embed and ingest every non-empty line under ``folder``."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    records = list(iter_documents(root))
    if not records:
        raise SystemExit(f"No scripture documents found under: {root}")

    documents = [content for content, _ in records]
    metadatas = [metadata for _, metadata in records]
    client = OpenAI()
    raw_embeddings = embed_all(client, documents, openai_model, batch_size)
    embeddings, means = centered_unit_vectors_by_book(raw_embeddings, metadatas)

    persist_path = Path(persist_dir).expanduser()
    persist_path.mkdir(parents=True, exist_ok=True)
    (persist_path / MEAN_FILENAME).write_text(json.dumps(means), encoding="utf-8")

    chroma_client = chromadb.PersistentClient(path=str(persist_path))
    collection = chroma_client.get_or_create_collection(
        name=chroma_collection_name,
        # Embeddings are already computed and normalized by this script.
        embedding_function=None,
        metadata={"embedding_model": openai_model, "mean_centered": "per_book"},
    )

    ids = [str(metadata["file_path"]) + f"::line_{metadata['verse']}"
           for metadata in metadatas]
    # Chroma imposes a maximum batch size for writes. This is separate from
    # the OpenAI embedding batch size above.
    max_chroma_batch_size = chroma_client.get_max_batch_size()
    for start in range(0, len(ids), max_chroma_batch_size):
        end = start + max_chroma_batch_size
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )

    print(
        f"Ingested {len(records)} documents into '{chroma_collection_name}' "
        f"(persisted at '{persist_path}')."
    )


def query_whole_documents(
        chroma_dir: str,
        collection: str,
        query: str,
        n_results: int = 10,
) -> list[dict[str, Any]]:
    """Query book-centered embeddings and return every hit with its metadata."""
    persist_path = Path(chroma_dir).expanduser()
    mean_path = persist_path / MEAN_FILENAME
    if not mean_path.is_file():
        raise SystemExit(f"Missing embedding mean: {mean_path}; ingest first")

    means: dict[str, list[float]] = json.loads(
        mean_path.read_text(encoding="utf-8")
    )
    chroma_client = chromadb.PersistentClient(path=str(persist_path))
    collection_obj = chroma_client.get_collection(name=collection)
    embedding_model = (collection_obj.metadata or {}).get(
        "embedding_model", DEFAULT_MODEL
    )

    client = OpenAI()
    raw_query = client.embeddings.create(
        model=embedding_model,
        input=[query],
    ).data[0].embedding

    # A query has to be transformed once for each book because each book has
    # its own mean embedding.
    hits: list[dict[str, Any]] = []
    for key, mean in means.items():
        centered = [
            value - mean_value
            for value, mean_value in zip(raw_query, mean)
        ]
        norm = math.sqrt(sum(value * value for value in centered))
        if norm == 0:
            raise ValueError(
                f"The query embedding has zero length after mean subtraction in {key}"
            )

        work, book = key.split("::", 1)
        results = collection_obj.query(
            query_embeddings=[[value / norm for value in centered]],
            where={"$and": [{"work": work}, {"book": book}]},
            n_results=n_results,
            include=["metadatas", "distances"],
        )
        hits.extend(
            {"distance": distance, "metadata": metadata}
            for distance, metadata in zip(
                results["distances"][0], results["metadatas"][0]
            )
        )

    hits.sort(key=lambda hit: hit["distance"])
    return hits[:n_results]


@wraps(query_whole_documents)
def _cli_query(*args, **kwargs):
    hits = query_whole_documents(*args, **kwargs)
    return "".join(
        f"({hit['distance']:.2f}) {hit['metadata']['book']} "
        f"{hit['metadata']['chapter']}:{hit['metadata']['verse']}\n"
        f"{hit['metadata']['content']}\n\n"
        for hit in hits
    )


if __name__ == "__main__":
    import fire

    fire.Fire({
        "ingest": ingest_folder,
        "query": _cli_query,
    })
