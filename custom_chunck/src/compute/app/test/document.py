from file_convert import log
from file_convert import log_in_file
import shared
import file_convert
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
        file_convert.convertOciDocumentUnderstanding(value)
        return
    elif resourceExtension in [".pdf", ".txt", ".csv", ".md", "", ".docx", ".doc",".pptx", ".ppt", ".html"] or resourceName in ["_metadata_schema.json", "_all.metadata.json"] :
        # Simply copy the file to the agent bucket
        file_convert.convertUpload(value)
        return
    # elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
    #    file_convert.convertImage2Pdf(value)
    #    return    
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
        # This will create a SRT file in Object Storage that will create a second even with resourceExtension ".srt" 
        file_convert.convertOciSpeech(value)
        return
    elif resourceExtension in [".sitemap"]:
        # This will create a PDFs file in Object Storage with the content of each site (line) ".sitemap" 
        file_convert.convertChromeSelenium2Pdf(value)
        return   
    elif resourceExtension in [".crawler"]:
        # This will crawl all HTML pages of a website 
        file_convert.convertCrawler(value)
        return    
    elif resourceExtension in [".webp"]:
        # Convert webp to PNG
        file_convert.convertWebp2Png(value)
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
            result = file_convert.convertJson(value)
        elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
            result = file_convert.convertOciVision(value)
        else:
            result = file_convert.convertOciFunctionTika(value)

        if result:
            log_in_file("content", result["content"])
            if len(result["content"])==0:
                return 
            file_convert.convertUpload(value, result["content"], result["path"])    

    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        # No need to get the content for deleting
        file_convert.convertUpload(value, "-")    

    log( "</eventDocument>")

