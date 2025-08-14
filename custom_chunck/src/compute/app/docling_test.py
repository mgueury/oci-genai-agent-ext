from langchain_docling import DoclingLoader

FILE_PATH = "https://arxiv.org/pdf/2408.09869"

loader = DoclingLoader(file_path=FILE_PATH)

docs = loader.load()
for d in docs[:3]:
    print(f"- {d.page_content=}")

FILE_PATH = "https://raw.githubusercontent.com/oracle-devrel/oci-starter/refs/heads/main/README.md"

loader = DoclingLoader(
    file_path=FILE_PATH,
    export_type=ExportType.MARKDOWN,
    chunker=HybridChunker(tokenizer=EMBED_MODEL_ID),
)

from langchain_text_splitters import MarkdownHeaderTextSplitter

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ],
)
splits = [split for doc in docs for split in splitter.split_text(doc.page_content)]

for d in splits[:3]:
    print(f"- {d.page_content=}")

print("...")