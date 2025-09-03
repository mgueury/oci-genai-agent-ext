from shared_oci import log
from shared_oci import log_in_file
import shared
import shared_oci
import pathlib
import os

## -- getFileExtension ------------------------------------------------------

def getFileExtension(resourceName):
    lowerResourceName = resourceName.lower()
    return pathlib.Path(lowerResourceName).suffix

## -- eventDocument ---------------------------------------------------------

def eventDocument(value):
    log( "<eventDocument>")
    eventType = value["eventType"]
    # ex: /n/fr03kabcd/psql-public-bucket/o/country.pdf"
    resourceId = value["data"]["resourceId"]
    log( "eventType=" + eventType + " - " + resourceId ) 
    # eventType == "com.oraclecloud.objectstorage.createobject":
    # eventType == "com.oraclecloud.objectstorage.updateobject":
    # eventType == "com.oraclecloud.objectstorage.deleteobject":
    resourceName = value["data"]["resourceName"]
    resourceExtension = getFileExtension(resourceName)
    log( "Extension:" + resourceExtension )
     
    # Content 
    result = { "content": "-" }
    if resourceExtension in [".tif"] or resourceName.endswith(".anonym.pdf"):
        # This will create a JSON file in Object Storage that will create a second even with resourceExtension "json" 
        shared_oci.convertOciDocumentUnderstanding(value)
        return
    elif resourceExtension in [".pdf", ".txt", ".csv", ".md", "", ".docx", ".doc",".pptx", ".ppt", ".html"] or resourceName in ["_metadata_schema.json", "_all.metadata.json"] :
        # Simply copy the file to the agent bucket
        shared_oci.convertUpload(value)
        return
    # elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
    #    shared_oci.convertImage2Pdf(value)
    #    return    
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
        # This will create a SRT file in Object Storage that will create a second even with resourceExtension ".srt" 
        shared_oci.convertOciSpeech(value)
        return
    elif resourceExtension in [".sitemap"]:
        # This will create a PDFs file in Object Storage with the content of each site (line) ".sitemap" 
        shared_oci.convertSitemapText(value)
        return   
    elif resourceExtension in [".crawler"]:
        # This will crawl all HTML pages of a website 
        shared_oci.convertCrawler(value)
        return    
    elif resourceExtension in [".webp"]:
        # Convert webp to PNG
        shared_oci.convertWebp2Png(value)
        return
    elif resourceExtension in [".srt"]:
        log("IGNORE .srt")
        return
    elif resourceName.endswith("/"):
        # Ignore
        log("IGNORE /")
        return

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        if resourceExtension in [".json"]:
            result = shared_oci.convertJson(value)
        elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
            result = shared_oci.convertOciVision(value)
        else:
            result = shared_oci.convertOciFunctionTika(value)

        if result:
            log_in_file("content", result["content"])
            if len(result["content"])==0:
                return 
            shared_oci.convertUpload(value, result["content"], result["path"])    

    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        # No need to get the content for deleting
        shared_oci.convertUpload(value, "-")    

    log( "</eventDocument>")

## -- updateCount ------------------------------------------------------------------

countUpdate = 0

def updateCount(count):
    ## XXX Not needed for DB23ai ? And/or bulk calculate the Embedding via a PLSQL procedure ?
    global countUpdate
    if count>0:
        countUpdate = countUpdate + count 
    elif countUpdate>0:
        try:
            # shared.genai_agent_datasource_ingest()
            # log( "<updateCount>GenAI agent datasource ingest job created")
            countUpdate = 0
        except (Exception) as e:
            log(f"\u26A0 <updateCount>ERROR: {e}")
