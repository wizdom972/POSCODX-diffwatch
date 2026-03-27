"""
RAG 검색 도구 — documents/ 폴더의 문서를 벡터 스토어에 인덱싱하고 검색 도구를 제공합니다.

지원 형식: .md, .pdf

사용법:
    from rag.retriever import get_rag_tools
    tools += get_rag_tools()
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# ─── 설정 ────────────────────────────────────────────────────
DOCUMENTS_DIR = Path(__file__).parent / "documents"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 3

# ─── 벡터 스토어 (모듈 로드 시 1회 구축) ────────────────────
_vector_store = None


def _load_md(path: Path) -> Document:
    """마크다운 파일을 Document로 로드합니다."""
    content = path.read_text(encoding="utf-8")
    return Document(page_content=content, metadata={"source": path.name})


def _load_pdf(path: Path) -> Document:
    """PDF 파일을 Document로 로드합니다."""
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    content = "\n\n".join(pages)
    return Document(page_content=content, metadata={"source": path.name})


_LOADERS = {
    ".md": _load_md,
    ".pdf": _load_pdf,
}


def _build_vector_store() -> InMemoryVectorStore:
    """documents/ 폴더의 .md / .pdf 파일들을 로드하여 벡터 스토어를 구축합니다."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    # 문서 로드
    docs = []
    for file in sorted(DOCUMENTS_DIR.iterdir()):
        loader = _LOADERS.get(file.suffix.lower())
        if loader:
            docs.append(loader(file))

    if not docs:
        raise FileNotFoundError(
            f"rag/documents/ 폴더에 지원되는 문서가 없습니다 ({', '.join(_LOADERS)}): {DOCUMENTS_DIR}"
        )

    # 청킹
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    splits = splitter.split_documents(docs)

    # 벡터 스토어 구축
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    _vector_store = InMemoryVectorStore.from_documents(splits, embeddings)

    print(f"[RAG] 벡터 스토어 구축 완료: {len(docs)}개 문서 → {len(splits)}개 청크")
    return _vector_store


# ─── 검색 도구 ────────────────────────────────────────────────
@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """지식 베이스에서 관련 문서를 검색합니다. 사내 규정이나 회사 정책에 대한 질문이 들어오면 이 도구를 사용하세요.

    Args:
        query: 검색할 내용
    """
    vs = _build_vector_store()
    results = vs.similarity_search(query, k=TOP_K)
    text = "\n\n".join(
        f"[{d.metadata['source']}] {d.page_content}" for d in results
    )
    return text, results


def add_documents_to_store(documents: list) -> None:
    """벡터 스토어에 문서를 동적으로 추가합니다.
    현재 세션 내에서 즉시 검색 가능하도록 인메모리 스토어에 반영합니다.

    Args:
        documents: 추가할 Document 객체 목록
    """
    vs = _build_vector_store()
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    splits = splitter.split_documents(documents)
    vs.add_documents(splits)
    print(f"[RAG] 문서 {len(documents)}개 추가 → {len(splits)}개 청크")


def get_rag_tools() -> list:
    """RAG 검색 도구 리스트를 반환합니다."""
    # 벡터 스토어를 미리 구축 (첫 호출 시)
    _build_vector_store()
    return [retrieve]
