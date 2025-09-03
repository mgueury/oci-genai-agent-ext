from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

DOC_SOURCE = "https://arxiv.org/pdf/2206.01062"

converter = DocumentConverter()
doc = converter.convert(source=DOC_SOURCE).document

chunker = HybridChunker()
chunk_iter = chunker.chunk(dl_doc=doc)

for i, chunk in enumerate(chunk_iter):
    if i < 10:
        page_numbers = sorted(
            set(
                prov.page_no
                for item in chunk.meta.doc_items
                for prov in item.prov
                if hasattr(prov, "page_no")
            )
        )
        print(f"Chunk {i}, text: {repr(chunker.serialize(chunk)[:40])}…, Page Numbers: {page_numbers}")