from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_text_splitters import MarkdownHeaderTextSplitter
from docling.chunking import HierarchicalChunker
from docling.chunking import HybridChunker

def split_document( path ):
    loader = DoclingLoader(
        file_path=path,
        export_type=ExportType.MARKDOWN,
    #     chunker=HybridChunker(tokenizer=EMBED_MODEL_ID),
    )
    docs = loader.load()
    print("-- DOCS --")    
    for d in docs:
        print(f"- {d.page_content=}")
    print("-- SPLITS --")    
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ],
    )
    splits = [split for doc in docs for split in splitter.split_text(doc.page_content)]
    for d in splits:
        print(f"- {str(d)}")
    print("-----")

def split_document2( path ):
    loader = DoclingLoader(
        file_path=path,
        export_type=ExportType.DOC_CHUNKS,
        chunker=HybridChunker()
    )
    docs = loader.load()
    print("-- DOCS --")    
    for d in docs:
        print(f"- {str(d)}")
    print("-----")

split_document( "https://raw.githubusercontent.com/oracle-devrel/oci-starter/refs/heads/main/README.md" )
split_document2( "https://raw.githubusercontent.com/oracle-devrel/oci-starter/refs/heads/main/README.md" )
split_document2( "https://arxiv.org/pdf/2408.09869" )

