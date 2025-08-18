

from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType

## -- docling2md ------------------------------------------------------------


def docling2md(value):
    log("<docling2md>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceId = value["data"]["resourceId"]
    resourceGenAI = str(Path(resourceName).with_suffix('.md'))
      
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        # Set the original URL source (GenAI Agent)
        metadata = get_metadata_from_resource_id( resourceId )
        orig_file = download_file( namespace, bucketName, resourceName)     
        dest_file = LOG_DIR+"/"+UNIQUE_ID+".md"
        loader = DoclingLoader(
            file_path=orig_file,
            export_type=ExportType.MARKDOWN
        )
        docs = loader.load()        
        value["content"] = ""
        for d in docs:
            value["content"] = value["content"] + d.page_content
        with open(dest_file, 'w', encoding='utf-8') as f_out:
            f_out.write(value["content"])       
        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=dest_file, content_type="text/markdown", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<docling2md> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log("</docling2md>")



