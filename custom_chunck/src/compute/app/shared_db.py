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
from typing import List, Tuple

# Globals
embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com",
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

        if extension in [ ".txt", ".md", ".html", ".htm" ]:
            loader = TextLoader( file_path=file_path )
            docs = loader.load()
        elif extension in [ ".pdf" ]:
            # loader = PyPDFLoader(
            #     file_path,
            #     mode="single",
            #     pages_delimiter="\n-------THIS IS A CUSTOM END OF PAGE-------\n",
            loader = PyPDFLoader(
                file_path,
                mode="page"
            )
            docs = loader.load()
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
        print(len(docs))
        print("-- medata --------------------")
        pprint.pp(docs[0].metadata)
        deleteDoc( value ) 
        insertTableDocs(value)
        insertTableDocsChunck(value, docs)  


# -- insertTableDocs -----------------------------------------------------------------
# Normal insert

def insertTableDocs( value ):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO docs (
            application_name, author, translation, content, content_type,
            creation_date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, summary, source_type
        )
        VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17)
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

def insertTableDocsChunck(value, docs):  
    
    global dbConn
    log("<langchain insertDocsChunck>")
    print("-- docs --------------------")
    pprint.pp(docs)
    vectorstore = OracleVS( client=dbConn, table_name="docs_langchain", embedding_function=embeddings, distance_strategy=DistanceStrategy.DOT_PRODUCT )
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)      
    for doc in docs:
        doc.metadata["doc_id"] = dictString(value,"docId")
        doc.metadata["file_name"] = value["data"]["resourceName"]
        doc.metadata["path"] = value["customized_url_source"]
        doc.metadata["content_type"] = dictString(value,"contentType")
    print("-- docs --------------------")
    pprint.pp(docs)
    docs_chunck = text_splitter.split_documents(docs)
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
