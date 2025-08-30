# Import
import os
import array
import pprint
import oracledb
import pathlib
from shared import log
from shared import dictString
from shared import dictInt

# Langchain
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_core.documents import Document
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import DistanceStrategy

# Docling
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_text_splitters import MarkdownHeaderTextSplitter

from typing import List, Tuple

# Globals
region = os.getenv("TF_VAR_region")
embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai."+region+".oci.oraclecloud.com",
    compartment_id=os.getenv("TF_VAR_compartment_ocid"),
    auth_type="INSTANCE_PRINCIPAL"
)

# Connection
dbConn = None

## -- initDbConn --------------------------------------------------------------

def initDbConn():
    global dbConn 
    # Thick driver...
    # oracledb.init_oracle_client()
    dbConn = oracledb.connect( user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), dsn=os.getenv('DB_URL'))
    dbConn.autocommit = True

## -- closeDbConn --------------------------------------------------------------

def closeDbConn():
    global dbConn 
    dbConn.close()

# -- insertDoc -----------------------------------------------------------------
# See https://python.langchain.com/docs/integrations/document_loaders/

def insertDoc( value, file_path, object_name ):
    if file_path:
        extension = pathlib.Path(object_name.lower()).suffix
        resourceName = value["data"]["resourceName"]

        if resourceName in ["_metadata_schema.json", "_all.metadata.json"]:
            return
        elif extension in [ ".txt", ".json", ".md" ]:
            loader = TextLoader( file_path=file_path )
        elif extension in [ ".html", ".htm" ]:
            loader = DoclingLoader(
                file_path=file_path,
                export_type=ExportType.MARKDOWN
            )            
        elif extension in [ ".pdf" ]:
            # loader = PyPDFLoader(
            #     file_path,
            #     mode="single",
            #     pages_delimiter="\n-------THIS IS A CUSTOM END OF PAGE-------\n",
            loader = PyPDFLoader(
                file_path,
                mode="page"
            )
            # loader = PyPDFLoader(
            #     file_path,
            #     mode="single",
            #     pages_delimiter="\n-------THIS IS A CUSTOM END OF PAGE-------\n",
            # )
            # docs = loader.load()
            # print(docs[0].page_content[:5780])
        else:
            log(f"<insertDoc> Error: unknown extension: {extension}")
            return
        docs = loader.load()        

        value["content"] = ""
        for d in docs:
            value["content"] = value["content"] + d.page_content
        value["source_type"] = "OBJECT_STORAGE"

        # Summary 
        if len(value["content"])>250:
            value["summary"] = shared.summarizeContent(value, value["content"])
        else:    
            value["summary"] = value["content"]            
        value["summaryEmbed"] = embeddings.embed_query(value["summary"])

        print(len(docs))
        print("-- doc[0].metadata --------------------")
        pprint.pp(docs[0].metadata)
        deleteDoc( value ) 
        insertTableDocs(value)
        insertTableDocsChunck(value, docs, extension)  

# -- insertTableDocs -----------------------------------------------------------------
# Normal insert

def insertTableDocs( value ):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO docs (
            application_name, author, translation, content, content_type,
            creation_date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, summary, summary_embed, source_type
        )
        VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18)
        RETURNING id INTO :18
    """
    id_var = cur.var(oracledb.NUMBER)
    data = (
            dictString(value,"applicationName"), 
            dictString(value,"author"),
            dictString(value,"translation"),
            # array.array("f", result["summaryEmbed"]),
            dictString(value,"content"),
            dictString(value,"contentType"),
            dictString(value,"creationDate"),
            dictString(value,"modified"),
            dictString(value,"other1"),
            dictString(value,"other2"),
            dictString(value,"other3"),
            dictString(value,"parsed_by"),
            dictString(value,"resourceName"), # filename
            dictString(value,"customized_url_source"), # path
            dictString(value,"publisher"),
            os.getenv("TF_VAR_region"),
            dictString(value,"summary"),
            dictString(value,"summaryEmbed"),            
            dictString(value,"source_type"),
            id_var
        )
    try:
        cur.execute(stmt, data)
        # Get generated id
        id = id_var.getvalue()    
        log("<insertDocs> returning id=" + str(id[0]) )        
        value["docId"] = id[0]
        log(f"<insertDocs> Successfully inserted {cur.rowcount} records.")
    except (Exception) as error:
        log(f"<insertDocs> Error inserting records: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- insertTableDocsChunck -----------------------------------------------------------------

def insertTableDocsChunck(value, docs, extension):  
    
    global dbConn
    log("<langchain insertDocsChunck>")
    print("-- docs --------------------")
    pprint.pp(docs)

    vectorstore = OracleVS( client=dbConn, table_name="docs_langchain", embedding_function=embeddings, distance_strategy=DistanceStrategy.DOT_PRODUCT )

    if extension in [ ".md", ".html", ".htm" ]:
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header_1"),
                ("##", "Header_2"),
                ("###", "Header_3"),
            ],
        )
        docs_chunck = [split for doc in docs for split in splitter.split_text(doc.page_content)]
    else:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)      
        docs_chunck = splitter.split_documents(docs)

    for d in docs_chunck:
        d.metadata["doc_id"] = dictString(value,"docId")
        d.metadata["file_name"] = value["data"]["resourceName"]
        d.metadata["path"] = value["customized_url_source"]
        d.metadata["content_type"] = dictString(value,"contentType")

    print("-- docs_chunck --------------------")  
    pprint.pp( docs_chunck )
    vectorstore.add_documents( docs_chunck )
    log("</langchain insertDocsChunck>")

# -- deleteDoc -----------------------------------------------------------------

def deleteDoc( value ):  
    global dbConn
    cur = dbConn.cursor()
    path = value["customized_url_source"]
    log(f"<deleteDoc> path={path}")

    # Delete the document record
    try:
        cur.execute("delete from docs where path=:1", (path,))
        print(f"<deleteDoc> Successfully {cur.rowcount} docs deleted")
    except (Exception) as error:
        print(f"<deleteDoc> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

    # Delete from the table directly..
    cur = dbConn.cursor()
    stmt = "delete FROM docs_langchain WHERE JSON_VALUE(metadata,'$.path')=:1"
    log(f"<langchain deleteDoc> path={path}")
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDoc> langchain: Successfully {cur.rowcount} deleted")
    except (Exception) as error:
        print(f"<deleteDoc> langchain: Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()    

# -- queryDb ----------------------------------------------------------------------

def queryDb( type, question, embed ):
    result = [] 
    cursor = dbConn.cursor()
    about = "about("+question+")";
    if type=="search": 
        # Text search example
        query = """
        SELECT filename, path, TO_CHAR(content) content_char, content_type, region, page, summary, score(99) score FROM docs_chunck
        WHERE CONTAINS(content, :1, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        """
        cursor.execute(query,(about,))
    elif type=="semantic":
        query = """
        SELECT filename, path, TO_CHAR(content) content_char, content_type, region, page, summary, cohere_embed <=> :1 score FROM docs_chunck
            ORDER BY score FETCH FIRST 10 ROWS ONLY
        """
        cursor.execute(query,(array.array("f", embed),))
    else: # type in ["hybrid","rag"]:
        query = """
        WITH text_search AS (
            SELECT id, score(99)/100 as score FROM docs_chunck
            WHERE CONTAINS(content, :1, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        ),
        vector_search AS (
            SELECT id, cohere_embed <=> :2 AS vector_distance
            FROM docs_chunck
        )
        SELECT o.filename, o.path, TO_CHAR(content) content_char, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.score + 0.7 * (1 - vs.vector_distance)) AS score
        FROM docs_chunck o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY score DESC
        FETCH FIRST 10 ROWS ONLY
        """
        cursor.execute(query,(about,array.array("f", embed),))
#        FULL OUTER JOIN text_search ts ON o.id = ts.id
#        FULL OUTER JOIN vector_search vs ON o.id = vs.id
    rows = cursor.fetchall()
    for row in rows:
        result.append( {"filename": row[0], "path": row[1], "content": str(row[2]), "contentType": row[3], "region": row[4], "page": row[5], "summary": str(row[6]), "score": row[7]} )  
    for r in result:
        log("filename="+r["filename"])
        log("content: "+r["content"][:150])
    return result


# -- getDocByPath ----------------------------------------------------------------------

def getDocByPath( path ):
    query = "SELECT filename, path, content, content_type, region, summary FROM docs WHERE path=:1"
    cursor = dbConn.cursor()
    cursor.execute(query,(path,))
    rows = cursor.fetchall()
    for row in rows:
        log("<getDocByPath>" + str(row[2]))
        return str(row[2])  
    log("<getDocByPath>Docs not found: " + path)
    return "-"  
