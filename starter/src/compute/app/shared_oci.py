# Import
import os
import json 
import requests
import oci
import csv
import time
from datetime import datetime
from pathlib import Path
from oci.object_storage.transfer.constants import MEBIBYTE
import urllib.parse

# Anonymization
import anonym_pdf
from PIL import Image
import subprocess
import shared_db

# Sitemap
import base64
import pdfkit
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Shared
from shared import log
from shared import log_in_file
from shared import dictString
from shared import dictInt
from shared import LOG_DIR
from shared import signer
from shared import UNIQUE_ID

## -- find_executable_path --------------------------------------------------

def find_executable_path(prefix):
    for path in os.environ['PATH'].split(os.pathsep):
        try:
            for filename in os.listdir(path):
                if filename.startswith(prefix) and os.access(os.path.join(path, filename), os.X_OK) and os.path.isfile(os.path.join(path, filename)):
                   return os.path.join(path, filename)
        except:
            continue
    return None

## -- CONSTANTS -------------------------------------------------------------

libreoffice_exe = find_executable_path("libreoffice")

## -- delete_bucket_folder --------------------------------------------------

def delete_bucket_folder(namespace, bucketName, prefix):
    log( "<delete_bucket_folder> "+prefix)
    try:
        os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)    
        response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketName, prefix=prefix, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
        for object_file in response.data.objects:
            f = object_file.name
            log( "<delete_bucket_folder> Deleting: " + f )
            os_client.delete_object( namespace_name=namespace, bucket_name=bucketName, object_name=f )
            log( "<delete_bucket_folder> Deleted: " + f )
    except:
        log("Exception: delete_bucket_folder") 
        log(traceback.format_exc())            
    log( "</delete_bucket_folder>" )

## -- get_metadata_from_resource_id -----------------------------------------
def get_metadata_from_resource_id( resourceId ):
    region = os.getenv("TF_VAR_region")
    customized_url_source = "https://objectstorage."+region+".oraclecloud.com" + resourceId
    return get_upload_metadata( customized_url_source )

## -- get_upload_metadata ---------------------------------------------------

def get_upload_metadata( customized_url_source ):
    log( "customized_url_source="+customized_url_source )
    customized_url_source = urllib.parse.quote(customized_url_source, safe=':/', encoding=None, errors=None)
    log( "After encoding="+customized_url_source )
    folder = os.path.dirname( '/' + customized_url_source.split("/o/",1)[1] )
    log( "folder="+folder )
    # Add folder metadata
    # See https://docs.oracle.com/en-us/iaas/Content/generative-ai-agents/RAG-tool-object-storage-guidelines.htm
    return {'customized_url_source': customized_url_source, 'gaas-metadata-filtering-field-folder': folder}

## -- convertOciFunctionTika ------------------------------------------------

def convertOciFunctionTika(value):
    global signer
    log( "<convertOciFunctionTika>")
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    invoke_client = oci.functions.FunctionsInvokeClient(config = {}, service_endpoint=fnInvokeEndpoint, signer=signer)
    # {"bucketName": "xxx", "namespace": "xxx", "resourceName": "xxx"}
    req = '{"bucketName": "' + bucketName + '", "namespace": "' + namespace + '", "resourceName": "' + resourceName + '"}'
    log( "Tika request: " + req)
    resp = invoke_client.invoke_function(fnOcid, invoke_function_body=req.encode("utf-8"))
    text = resp.data.text.encode('iso-8859-1').decode('utf-8')
    log_in_file("tika_resp", text) 
    j = json.loads(text)
    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "applicationName": "Tika Parser",
        "modified": UNIQUE_ID,
        "contentType": dictString(j,"Content-Type"),
        "parsedBy": dictString(j,"X-Parsed-By"),
        "creationDate": UNIQUE_ID,
        "author": dictString(j,"Author"),
        "publisher": dictString(j,"publisher"),
        "content": j["content"],
        "path": resourceId
    }
    log( "</convertOciFunctionTika>")
    return result

   
## -- convertOciVision --------------------------------------------------------------

def convertOciVision(value):
    log( "<convertOciVision>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log_in_file("vision_resp", str(resp.data)) 

    concat_imageText = ""
    for l in resp.data.image_text.lines:
      concat_imageText += l.text + " "
    log("concat_imageText: " + concat_imageText )

    concat_labels = ""
    for l in resp.data.labels:
      concat_labels += l.name + " "
    log("concat_labels: " +concat_labels )

    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "Image",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": concat_imageText + " " + concat_labels,
        "path": resourceId,
        "other1": concat_labels
    }
    log( "</convertOciVision>")
    return result    

## -- convertOciVisionBelgianID --------------------------------------------------------------

def convertOciVisionBelgianID(value):
    log( "<convertOciVisionBelgianID>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log(resp.data)
    # log(json.dumps(resp,sort_keys=True, indent=4))

    name = resp.data.image_text.lines[8]
    id = resp.data.image_text.lines[19]
    birthdate = resp.data.image_text.lines[22]

    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "convertOciVisionBelgianID ID",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": "convertOciVisionBelgianID identity card. Name="+name,
        "path": resourceId,
        "other1": id,
        "other2": birthdate,
    }
    log( "</convertOciVisionBelgianID>")
    return result  

## -- convertOciSpeech ------------------------------------------------------

def convertOciSpeech(value):
    log( "<convertOciSpeech>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    prefix = resourceName + ".speech"

    if eventType in [ "com.oraclecloud.objectstorage.updateobject", "com.oraclecloud.objectstorage.deleteobject" ]:
        # Delete previous speech conversion 
        delete_bucket_folder( namespace, bucketName, prefix )

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        job = {
            "normalization": {
                    "isPunctuationEnabled": True
            },
            "compartmentId": compartmentId,
            "displayName": UNIQUE_ID,
            "modelDetails": {
                    "domain": "GENERIC",
                    "languageCode": "en-US"
            },
            "inputLocation": {
                    "locationType": "OBJECT_LIST_INLINE_INPUT_LOCATION",
                    "objectLocations": [
                        {
                                "namespaceName": namespace,
                                "bucketName": bucketName,
                                "objectNames": [
                                    resourceName
                                ]
                        }
                    ]
            },
            "outputLocation": {
                    "namespaceName": namespace,
                    "bucketName": bucketName,
                    "prefix": prefix
            },
            "additionalTranscriptionFormats": [
                    "SRT"
            ]
        }
        speech_client = oci.ai_speech.AIServiceSpeechClient(config = {}, signer=signer)
        resp = speech_client.create_transcription_job(job)
        log_in_file("speech_resp",str(resp.data))

    log( "</convertOciSpeech>")

## -- convertOciDocumentUnderstanding ---------------------------------------

def convertOciDocumentUnderstanding(value):

    log( "<convertOciDocumentUnderstanding>")
    eventType = value["eventType"]    
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    prefix = resourceName +".docu"

    if eventType in [ "com.oraclecloud.objectstorage.updateobject", "com.oraclecloud.objectstorage.deleteobject" ]:
        # Delete previous speech conversion 
        delete_bucket_folder( namespace, bucketName, prefix )

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        job = {
            "processorConfig": {
                "language": "ENG",
                "processorType": "GENERAL",
                "features": [
                    {
                        "featureType": "TEXT_EXTRACTION"
                    }
                ],
                "isZipOutputEnabled": False
            },
            "compartmentId": compartmentId,
            "inputLocation": {
                "sourceType": "OBJECT_STORAGE_LOCATIONS",
                "objectLocations": [
                    {
                        "bucketName": bucketName,
                        "namespaceName": namespace,
                        "objectName": resourceName
                    }
                ]
            },
            "outputLocation": {
                "namespaceName": namespace,
                "bucketName": bucketName,
                "prefix": prefix
            }
        }
        document_understanding_client = oci.ai_document.AIServiceDocumentClient(config = {}, signer=signer)
        resp = document_understanding_client.create_processor_job(job)
        log_in_file("convertOciDocumentUnderstanding_resp",str(resp.data))
    log( "</convertOciDocumentUnderstanding>")

## -- chrome_webdriver ---------------------------------------------------

def chrome_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-notifications")    
    options.add_argument(f"--user-data-dir=/home/opc/chrome_profile")
    settings = {
        "recentDestinations": [{
                "id": "Save as PDF",
                "origin": "local",
                "account": "",
            }],
            "selectedDestinationId": "Save as PDF",
            "version": 2
        }
    prefs = {
        'printing.print_preview_sticky_settings.appState': json.dumps(settings),
        'savefile.default_directory': '/tmp/',
        'download.default_directory': '/tmp/',
        'plugins.plugins_disabled': "Chrome PDF Viewer",
        'plugins.always_open_pdf_externally': "true"
    }    
    options.add_experimental_option('prefs', prefs)
    options.add_argument('--kiosk-printing')  
    driver = webdriver.Chrome(options=options)
    return driver

## -- chrome_download_url_as_pdf ---------------------------------------------------
def chrome_download_url_as_pdf( driver, url, output_filename):
    driver.get(url)
    driver.implicitly_wait(15) 
    try:
        element_present = EC.presence_of_element_located((By.TAG_NAME, 'body'))
        WebDriverWait(driver, 20).until(element_present) 
    except Exception as e:
        print(f"Error waiting for element: {e}")    

    print_options = {
        "marginsType": 1,         # Set margins (0 = default, 1 = no margins, 2 = minimal margins)
        "printBackground": False  # Print background graphics
    }
    params = {'behavior': 'default', 'downloadPath': os.getcwd()} # Set the download directory to current working directory
    driver.execute_cdp_cmd('Page.setDownloadBehavior', params) # Set the download path for the PDF
    result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
    pdf_data = result['data']
    with open(output_filename, "wb") as f:
        f.write(bytes(base64.b64decode(pdf_data)))
    log(f"<chrome_download_url_as_pdf> Saved {output_filename}")   

## -- convertSitemapText ----------------------------------------------------
def convertSitemapText(value):

    # Read the SITEMAP file from the object storage
    # The format of the file expected is a txt file. Each line contains a full URI.
    # Transforms all the links in PDF and reupload them as PDF in the same object storage
    log( "<convertSitemapText>")
    eventType = value["eventType"]     
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceName = value["data"]["resourceName"]
    prefix=resourceName+".download"

    if eventType in [ "com.oraclecloud.objectstorage.updateobject", "com.oraclecloud.objectstorage.deleteobject" ]:
        # Delete previous speech conversion 
        delete_bucket_folder( namespace, bucketGenAI, prefix )
    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:         
        fileList = []

        os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

        resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
        folder = resourceName
        file_name = LOG_DIR+"/"+UNIQUE_ID+".sitemap"
        with open(file_name, 'wb') as f:
            for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)

        if os.getenv("INSTALL_LIBREOFFICE")!="no":
            driver = chrome_webdriver()
        try:
            with open(file_name, 'r') as f:
                for line in f:
                    try:
                        line = line.strip()  # Remove leading/trailing whitespace
                        # Handle empty lines gracefully
                        if not line:
                            continue

                        full_uri = line

                        # Print the filename with the ".pdf" extension
                        pdf_path = full_uri
                        # Remove trailing /
                        last_char = pdf_path[-1:]
                        if last_char == '/':
                            pdf_path = pdf_path[:-1]

                        pdf_path = pdf_path.replace('/', '___');
                        pdf_path = pdf_path+'.pdf'
                        log("<convertSitemapText>"+full_uri)
                        if os.getenv("INSTALL_LIBREOFFICE")!="no":
                            chrome_download_url_as_pdf( driver, full_uri, LOG_DIR+'/'+pdf_path)
                        else:
                            pdfkit.from_url(full_uri, LOG_DIR+"/"+pdf_path)
    
                        metadata=  {'customized_url_source': full_uri, 'gaas-metadata-filtering-field-folder': folder }    

                        # Upload to object storage as "site/"+pdf_path
                        upload_file(value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+pdf_path, file_path=LOG_DIR+"/"+pdf_path, content_type='application/pdf', metadata=metadata)
                        fileList.append( prefix+"/"+pdf_path )

    #                    with open(LOG_DIR+"/"+pdf_path, 'rb') as f2:
    #                        obj = os_client.put_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+pdf_path, put_object_body=f2, metadata=metadata)
                        
                    except Exception as e:
                        log("<convertSitemapText>Error parsing line: "+line+" in "+resourceName)
                        log("<convertSitemapText>Exception:" + str(e))

            # Check if there are file that are in the folder and not in the sitemap
            response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketGenAI, prefix=prefix, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
            for object_file in response.data.objects:
                f = object_file.name
                if f in fileList:
                    fileList.remove(f)
                else: 
                    log( "<convertSitemapText>Deleting: " + f )
                    os_client.delete_object( namespace_name=namespace, bucket_name=bucketGenAI, object_name=f )
                    log( "<convertSitemapText>Deleted: " + f )

        except FileNotFoundError as e:
            log("<convertSitemapText>Error: File not found= "+file_name)
        except Exception as e:
            log("<convertSitemapText>An unexpected error occurred: " + str(e))
        if os.getenv("INSTALL_LIBREOFFICE")!="no":    
            driver.quit()            
    log( "</convertSitemapText>")


## -- convertJson ------------------------------------------------------------------

def convertJson(value):
    log( "<convertJson>")
    global signer
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    
    log(f"<convertJson>namespace={namespace}" )
    log(f"<convertJson>bucketName={bucketName}" )
    log(f"<convertJson>resourceName={resourceName}" )
    # Read the JSON file from the object storage
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
    file_name = LOG_DIR+"/"+UNIQUE_ID+".json"
    with open(file_name, 'wb') as f:
        for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)

    with open(file_name, 'r') as f:
        file_content = f.read()
    log("Read file from object storage: "+ file_name)
    j = json.loads(file_content)   

    if ".docu/" in resourceName:
        # DocUnderstanding
        original_resourcename = resourceName[:resourceName.index(".json")][resourceName.index("/results/")+9:]
        original_resourceid = "/n/" + namespace + "/b/" + bucketName + "/o/" + original_resourcename
        if original_resourcename.endswith(".anonym.pdf"):
            anonym_pdf_file = download_file( namespace, bucketName, original_resourcename)
            pdf_file = anonym_pdf.remove_entities(anonym_pdf_file, j)
            # Upload the anonymize file in the public bucket.
            resourceName = original_resourcename.replace(".anonym.pdf", ".pdf") 
            upload_manager = oci.object_storage.UploadManager(os_client, max_parallel_uploads=10)
            upload_manager.upload_file(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName, file_path=pdf_file, part_size=2 * MEBIBYTE, content_type="application/pdf")
            return None  
        else: 
            concat_text = ""
            pages = {}
            for p in j.get("pages"):
                pageNumber = p.get("pageNumber")
                page = ""
                for l in p.get("lines"):
                    page += l.get("text") + "\n"
                pages[str(pageNumber)] = page
                concat_text += page + " "    
            result = {
                "filename": original_resourcename,
                "date": UNIQUE_ID,
                "applicationName": "OCI Document Understanding",
                "modified": UNIQUE_ID,
                "contentType": j["documentMetadata"]["mimeType"],
                "creationDate": UNIQUE_ID,
                "content": concat_text,
                "pages": pages,
                "path": original_resourceid
            }            
    else:
        # Speech
        original_resourcename = resourceName[:resourceName.index(".json")][resourceName.index("bucket_")+7:]
        original_resourceid = "/n/" + namespace + "/b/" + bucketName + "/o/" + original_resourcename
        result = {
            "filename": original_resourcename,
            "date": UNIQUE_ID,
            "applicationName": "OCI Speech",
            "modified": UNIQUE_ID,
            "contentType": j["audioFormatDetails"]["format"],
            "creationDate": UNIQUE_ID,
            "content": j["transcriptions"][0]["transcription"],
            "path": original_resourceid
        }
    log( "</convertJson>")
    return result

## -- upload_file -----------------------------------------------------------

def upload_file( value, namespace_name, bucket_name, object_name, file_path, content_type, metadata ):
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    upload_manager = oci.object_storage.UploadManager(os_client, max_parallel_uploads=10)
    upload_manager.upload_file(namespace_name=namespace_name, bucket_name=bucket_name, object_name=object_name, file_path=file_path, part_size=2 * MEBIBYTE, content_type=content_type, metadata=metadata)
    log( "Uploaded "+object_name + " - " + content_type )
    value["customized_url_source"] = metadata.get("customized_url_source")
    shared_db.insertDoc( value, file_path, object_name )

## -- convertUpload ---------------------------------------------------

def convertUpload(value, content=None, path=None):

    log( "<convertUpload>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceName = value["data"]["resourceName"]
    resourceGenAI = resourceName
    
    if content:
        resourceGenAI = resourceGenAI + ".convert.txt"

    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        # Set the original URL source (GenAI Agent)
        if path==None:
            path = value["data"]["resourceId"]
        region = os.getenv("TF_VAR_region")
        customized_url_source = "https://objectstorage."+region+".oraclecloud.com" + path
        log( "customized_url_source="+customized_url_source )
        metadata = get_upload_metadata( customized_url_source )

        file_name = LOG_DIR+"/"+UNIQUE_ID+".tmp"
        if not content:
            contentType = value["contentType"]
            resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
            with open(file_name, 'wb') as f:
                for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
                    f.write(chunk)
        else:
            contentType = "text/html"
            with open(file_name, 'w') as f:
                f.write(content)

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=file_name, content_type=contentType, metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<convertUpload> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)     
    log( "</convertUpload>")                                  

## -- convertLibreoffice2Pdf ------------------------------------------------------------

def convertLibreoffice2Pdf(value):
    log( "<convertLibreoffice2Pdf>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceId = value["data"]["resourceId"]
    resourceGenAI = str(Path(resourceName).with_suffix('.pdf'))
      
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        office_file = download_file( namespace, bucketName, resourceName)
        log( f'libreoffice_exe={libreoffice_exe}' )
        cmd = [ libreoffice_exe ] + '--convert-to pdf --outdir'.split() + [LOG_DIR, office_file]
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p.wait(timeout=30)
        stdout, stderr = p.communicate()
        time.sleep(10) 
        pdf_file = str(Path(office_file).with_suffix('.pdf'))
        if os.path.exists(pdf_file):
            log( f"<convertLibreoffice2Pdf> pdf found {pdf_file}")
        else:
            raise subprocess.SubprocessError(stderr)
        metadata = get_metadata_from_resource_id( resourceId )
        log( "pdf_file=" + pdf_file )
        log( "metadata=" + str(metadata) )
        log( "resourceGenAI=" + resourceGenAI )
        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=pdf_file, content_type="application/pdf", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<convertLibreoffice2Pdf> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</convertLibreoffice2Pdf>")

## -- download_file ---------------------------------------------------------

def download_file(namespace,bucketName,resourceName):
    log( "<download_file>")
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
    # Remove the directory name
    file_name = LOG_DIR+"/"+os.path.basename(resourceName)
    # Download the file
    with open(file_name, 'wb') as f:
        for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)
    log( "</download_file>")            
    return file_name

## -- save_image_as_pdf -----------------------------------------------------

def save_image_as_pdf( file_name, images ):
    # Save image with PIL
    if len(images) == 1:
        images[0].save(file_name)
    else:
        im = images.pop(0)
        im.save(file_name, save_all=True,append_images=images)

# ---------------------------------------------------------------------------
def convertImage2Pdf(value, content=None, path=None):
    log( "<convertImage2Pdf>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    resourceGenAI = resourceName+".pdf"
  
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        # Set the original URL source (GenAI Agent)
        metadata = get_metadata_from_resource_id( resourceId )

        image_file = download_file( namespace, bucketName, resourceName)     
        image = Image.open(image_file)
        pdf_file = LOG_DIR+"/"+UNIQUE_ID+".pdf"
        save_image_as_pdf( pdf_file, [image] )         

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=pdf_file, content_type="application/pdf", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<convertImage2Pdf> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</convertImage2Pdf>")

## -- convertWebp2Png -----------------------------------------------------

def convertWebp2Png(value, content=None, path=None):
    log( "<convertWebp2Png>")
    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    resourceGenAI = resourceName+".png"
  
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:
        # Set the original URL source (GenAI Agent)
        metadata = get_metadata_from_resource_id( resourceId )

        image_file = download_file( namespace, bucketName, resourceName)     
        image = Image.open(image_file).convert("RGB")
        png_file = LOG_DIR+"/"+UNIQUE_ID+".png"
        image.save(png_file, "png")        

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketName, object_name=resourceGenAI, file_path=png_file, content_type="image/png", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<convertWebp2Png> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</convertWebp2Png>")    

## -- run_crawler ------------------------------------------------------------

def run_crawler(url):
    """
    Executes the spider and, upon completion, reads and
    prints the contents of the generated links.csv file.
    """
    # Define the command to run the Spider.
    # The command assumes you are running this script from the
    # root directory of the project (where scrapy.cfg is located).
    crawler_command = ['./crawler.sh', 'crawler_spider', url]
    
    # Define the path to the output CSV file.
    output_dir = '/tmp/crawler'
    csv_filename = 'links.csv'
    csv_file_path = os.path.join(output_dir, csv_filename)

    print("--- Starting Crawler. Please wait... ---")   
    try:
        # Run the command. The 'check=True' argument will raise an
        # exception if the command fails, which is good for error handling.
        result = subprocess.run(crawler_command, check=True, capture_output=True, text=True)
        print("\n--- Crawler finished successfully. ---")
        
    except subprocess.CalledProcessError as e:
        # Handle cases where the command fails.
        print(f"\n--- Error: Crawler command failed with return code {e.returncode} ---")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise

## -- convertCrawler ------------------------------------------------------------------
def convertCrawler(value):
    log( "<convertCrawler>")
    eventType = value["eventType"]     
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    bucketGenAI = bucketName.replace("-public-bucket","-agent-bucket")
    resourceName = value["data"]["resourceName"]
    prefix=resourceName+".download"

    if eventType in [ "com.oraclecloud.objectstorage.updateobject", "com.oraclecloud.objectstorage.deleteobject" ]:
        # Delete previous speech conversion 
        delete_bucket_folder( namespace, bucketGenAI, prefix )
    if eventType in [ "com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject" ]:         
        fileList = []

        os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)

        resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
        folder = resourceName
        file_name = LOG_DIR+"/"+UNIQUE_ID+".crawler"
        with open(file_name, 'wb') as f:
            for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)

        try:
            with open(file_name, 'r') as f:
                for line in f:
                    try:
                        line = line.strip()  # Remove leading/trailing whitespace
                        # Handle empty lines gracefully
                        if not line:
                            continue

                        full_uri = line
                        run_crawler(full_uri)
                        # Check if the CSV file was created by the spider.
                        CRAWLER_DIR='/tmp/crawler'
                        csv_file_path=CRAWLER_DIR+'/links.csv'
                        print(f"\n--- Reading data from '{csv_file_path}'... ---")
                       
                        # Open and read the CSV file.
                        if not os.path.exists(csv_file_path):
                            print(f"Error: The file '{csv_file_path}' was not created.")
                            print("Please check the spider's output for any errors.")
                            return

                        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                            # Use DictReader for easy access to columns by their header.
                            reader = csv.DictReader(csvfile)            
                            # Loop through each row and print the URL and filename.
                            for row in reader:
                                url = row.get('url', 'N/A')
                                filename = row.get('filename', 'N/A')
                                title = row.get('title', 'N/A')
                                filename = filename[len(CRAWLER_DIR)+1:]
                                print(f"URL: {url} - Filename: {filename}")
                                metadata=  {'customized_url_source': url, 'gaas-metadata-filtering-field-folder': folder } 
                                value["data"]["resourceName"] = title   
                                upload_file(value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+filename, file_path=CRAWLER_DIR+"/"+filename, content_type='text/html', metadata=metadata)
                                fileList.append(filename)
                        
                    except Exception as e:
                        log("<convertCrawler>Error parsing line: "+line+" in "+resourceName)
                        log("<convertCrawler>Exception:" + str(e))

            # Check if there are file that are in the folder and not in the crawler
            response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketGenAI, prefix=prefix, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
            for object_file in response.data.objects:
                f = object_file.name
                if f in fileList:
                    fileList.remove(f)
                else: 
                    log( "<convertCrawler>Deleting: " + f )
                    os_client.delete_object( namespace_name=namespace, bucket_name=bucketGenAI, object_name=f )
                    log( "<crawconvertCrawlerler>Deleted: " + f )

        except FileNotFoundError as e:
            log("<convertCrawler>Error: File not found= "+file_name)
        except Exception as e:
            log("<convertCrawler>An unexpected error occurred: " + str(e))     
    log( "</convertCrawler>")