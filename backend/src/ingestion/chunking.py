"""Split page text into overlapping LangChain text chunks."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_pages(pages: list[dict], chunk_size: int = 600, chunk_overlap: int = 100) -> list[dict]:
    """Split each page independently and keep its page number on every chunk."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for page in pages:
        for text in splitter.split_text(page["text"]):
            if text.strip():
                chunks.append({"text": text, "page_number": page["page_number"]})
    return chunks
