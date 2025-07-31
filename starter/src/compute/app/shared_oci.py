# Import
import os
import json 
import requests
import oci
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

## -- find_executable_path --------------------------------------------------------

def find_executable_path(prefix):
    for path in os.environ['PATH'].split(os.pathsep):
        try:
            for filename in os.listdir(path):
                if filename.startswith(prefix) and os.access(os.path.join(path, filename), os.X_OK) and os.path.isfile(os.path.join(path, filename)):
                   return os.path.join(path, filename)
        except:
            continue
    return None

## --------------------------------------------------------------------------------

# Constant
UNIQUE_ID = "ID"

# Signer
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}
libreoffice_exe = find_executable_path("libreoffice")

# Create Log directory
LOG_DIR = '/tmp/app_log'
if os.path.isdir(LOG_DIR) == False:
    os.mkdir(LOG_DIR) 

## -- log ------------------------------------------------------------------

def log(s):
   dt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
   print( "["+dt+"] "+ str(s), flush=True)

## -- log_in_file --------------------------------------------------------

def log_in_file(prefix, value):
    global UNIQUE_ID
    # Create Log directory
    if os.path.isdir(LOG_DIR) == False:
        os.mkdir(LOG_DIR)     
    filename = LOG_DIR+"/"+prefix+"_"+UNIQUE_ID+".txt"
    with open(filename, "w") as text_file:
        text_file.write(value)
    log("log file: " +filename )  

## -- dictString ------------------------------------------------------------

def dictString(d,key):
   value = d.get(key)
   if value is None:
       return "-"
   else:
       return value  
   
## -- dictInt ------------------------------------------------------------

def dictInt(d,key):
   value = d.get(key)
   if value is None:
       return 0
   else:
       return int(float(value))     


## -- appendChunk -----------------------------------------------------------

def appendChunck(result, text, char_start, char_end ):
    chunck = text[char_start:char_end]
    result.append( { "chunck": chunck, "char_start": char_start, "char_end": char_end } )
    log("chunck (" + str(char_start) + "-" + str(char_end-1) + ") - " + chunck)      

## -- cutInChunks -----------------------------------------------------------

def cutInChunks(text):
    result = []
    prev = ""
    i = 0
    last_good_separator = 0
    last_medium_separator = 0
    last_bad_separator = 0
    MAXLEN = 250
    char_start = 0
    char_end = 0

    i = 0
    while i<len(text)-1:
        i += 1
        cur = text[i]
        cur2 = prev + cur
        prev = cur

        if cur2 in [ ". ", ".[" , ".\n", "\n\n" ]:
            last_good_separator = i
        if cur in [ "\n" ]:          
            last_medium_separator = i
        if cur in [ " " ]:          
            last_bad_separator = i
        # log( 'cur=' + cur + ' / cur2=' + cur2 )
        if i-char_start>MAXLEN:
            char_end = i
            if last_good_separator > 0:
               char_end = last_good_separator
            elif last_medium_separator > 0:
               char_end = last_medium_separator
            elif last_bad_separator > 0:
               char_end = last_bad_separator
            # XXXX
            if text[char_end] in [ "[", "(" ]:
                appendChunck( result, text, char_start, char_end )
            else:     
                appendChunck( result, text, char_start, char_end )
            char_start=char_end 
            last_good_separator = 0
            last_medium_separator = 0
            last_bad_separator = 0
    # Last chunck
    appendChunck( result, text, char_start, len(text) )

    # Overlapping chuncks
    if len(result)==1:
        return result
    else: 
        result2 = []
        chunck_count=0
        chunck_start=0
        for c in result:
            chunck_count = chunck_count + 1
            if chunck_count==4:
                appendChunck( result2, text, chunck_start, c["char_end"] )
                chunck_start = c["char_start"]
                chunck_count = 0
        if chunck_count>0:
            appendChunck( result2, text, chunck_start, c["char_end"] )
        return result2

## -- embedText -------------------------------------------------------------

# Ideally all vectors should be created in one call
def embedText(c):
    global signer
    log( "<embedText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/embedText'
    body = {
        "inputs" : [ c ],
        "servingMode" : {
            "servingType" : "ON_DEMAND",
            "modelId" : "cohere.embed-multilingual-v3.0"
        },
        "truncate" : "START",
        "compartmentId" : compartmentId
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("embedText_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    log( "</embedText>")
    return dictString(j,"embeddings")[0] 

## -- generateText ----------------------------------------------------------

def generateText(prompt):
    global signer
    log( "<generateText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/generateText'
    body = {
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
            "servingType": "ON_DEMAND"
        },
        "inferenceRequest": {
            "prompt": prompt,
            "maxTokens": 600,
            "temperature": 0,
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "stopSequences": [],
            "runtimeType": "COHERE"
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("generateText_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["inferenceResponse"]["generatedTexts"][0]["text"]
    log( "</generateText>")
    return s

## -- llama_chat2 -----------------------------------------------------------

def llama_chat2(prompt):
    global signer
    log( "<llama_chat2>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/20231130/actions/chat'
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "meta.llama-3.3-70b-instruct",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "apiFormat": "GENERIC",
            "maxTokens": 600,
            "temperature": 0,
            "preambleOverride": "",
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "messages": [
                {
                    "role": "USER", 
                    "content": [
                        {
                            "type": "TEXT",
                            "text": prompt
                        }
                    ]
                }  
            ]
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("llama_chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]["text"]
    if s.startswith('```json'):
        start_index = s.find("{") 
        end_index = s.rfind("}")+1
        s = s[start_index:end_index]
    log( "</llama_chat2>")
    return s

## -- llama_chat ------------------------------------------------------------

def llama_chat(messages):
    ## XXXX DOES NOT WORK XXXX ?
    global signer
    log( "<llama_chat>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-plus-08-2024",
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "meta.llama-3.1-70b-instruct",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "maxTokens": 600,
            "temperature": 0,
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "messages": messages,
            "apiFormat": "GENERIC"
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("llama_chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]["text"]
    if s.startswith('```json'):
        start_index = s.find("{") 
        end_index = s.rfind("}")+1
        s = s[start_index:end_index]
    log( "</llama_chat>")
    return s

## -- cohere_chat -----------------------------------------------------------

def cohere_chat(prompt, chatHistory, documents):
    global signer
    log( "<cohere_chat>")

    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-plus-08-2024",
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "cohere.command-r-plus-08-2024",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "maxTokens": 600,
            "temperature": 0,
            "preambleOverride": "",
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "message": prompt,
            "chatHistory": chatHistory,
            "documents": documents,
            "apiFormat": "COHERE"
        }
    }
    log_in_file("cohere_chat_request", json.dumps(body)) 
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("cohere_chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]
    log( "</cohere_chat>")
    return s

## -- invokeTika ------------------------------------------------------------------

def invokeTika(value):
    global signer
    log( "<invokeTika>")
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
    log( "</invokeTika>")
    return result

## -- summarizeContent ------------------------------------------------------

def summarizeContent(value,content):
    log( "<summarizeContent>")
    global signer
    compartmentId = value["data"]["compartmentId"]
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/chat'
    # Avoid Limit of 4096 Tokens
    if len(content) > 12000:
        log( "Truncating to 12000 characters")
        content = content[:12000]

    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "cohere.command-r-plus-08-2024",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "maxTokens": 4000,
            "temperature": 0,
            "preambleOverride": "",
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "message": "Summarise the following text in 200 words.\n\n"+content,
            "apiFormat": "COHERE"
        }
    }
    try: 
        resp = requests.post(endpoint, json=body, auth=signer)
        resp.raise_for_status()
        log(resp)   
        log_in_file("summarizeContent_resp",str(resp.content)) 
        j = json.loads(resp.content)   
        log( "</summarizeContent>")
        return dictString(j,"summary") 
    except requests.exceptions.HTTPError as err:
        log("Exception: summarizeContent") 
        log(err.response.status_code)
        log(err.response.text)
        return "-"
    
## -- vision --------------------------------------------------------------

def vision(value):
    log( "<vision>")
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
    log( "</vision>")
    return result    

## -- belgian --------------------------------------------------------------

def belgian(value):
    log( "<belgian>")
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
        "contentType": "Belgian ID",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": "Belgian identity card. Name="+name,
        "path": resourceId,
        "other1": id,
        "other2": birthdate,
    }
    log( "</belgian>")
    return result  

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

## -- speech ----------------------------------------------------------------

def speech(value):
    log( "<speech>")
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

    log( "</speech>")

## -- documentUnderstanding -------------------------------------------------

def documentUnderstanding(value):

    log( "<documentUnderstanding>")
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
        log_in_file("documentUnderstanding_resp",str(resp.data))
    log( "</documentUnderstanding>")

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

## -- sitemap ------------------------------------------------------------------
def sitemap(value):

    # Read the SITEMAP file from the object storage
    # The format of the file expected is a txt file. Each line contains a full URI.
    # Transforms all the links in PDF and reupload them as PDF in the same object storage
    log( "<sitemap>")
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
                        log("<sitemap>"+full_uri)
                        if os.getenv("INSTALL_LIBREOFFICE")!="no":
                            chrome_download_url_as_pdf( driver, full_uri, LOG_DIR+'/'+pdf_path)
                        else:
                            pdfkit.from_url(full_uri, LOG_DIR+"/"+pdf_path)
    
                        metadata=  {'customized_url_source': full_uri, 'gaas-metadata-filtering-field-folder': folder }    

                        # Upload to object storage as "site/"+pdf_path
                        upload_file(value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+pdf_path, file_path=LOG_DIR+"/"+pdf_path, part_size=2 * MEBIBYTE, content_type='application/pdf', metadata=metadata)
                        fileList.append( prefix+"/"+pdf_path )

    #                    with open(LOG_DIR+"/"+pdf_path, 'rb') as f2:
    #                        obj = os_client.put_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+pdf_path, put_object_body=f2, metadata=metadata)
                        
                    except Exception as e:
                        log("<sitemap>Error parsing line: "+line+" in "+resourceName)
                        log("<sitemap>Exception:" + str(e))

            # Check if there are file that are in the folder and not in the sitemap
            response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketGenAI, prefix=prefix, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
            for object_file in response.data.objects:
                f = object_file.name
                if f in fileList:
                    fileList.remove(f)
                else: 
                    log( "<sitemap>Deleting: " + f )
                    os_client.delete_object( namespace_name=namespace, bucket_name=bucketGenAI, object_name=f )
                    log( "<sitemap>Deleted: " + f )

        except FileNotFoundError as e:
            log("<sitemap>Error: File not found= "+file_name)
        except Exception as e:
            log("<sitemap>An unexpected error occurred: " + str(e))
        if os.getenv("INSTALL_LIBREOFFICE")!="no":    
            driver.quit()            
    log( "</sitemap>")


## -- decodeJson ------------------------------------------------------------------

def decodeJson(value):
    log( "<decodeJson>")
    global signer
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    
    log(f"<decodeJson>resourceName={namespace}" )
    log(f"<decodeJson>resourceName={bucketName}" )
    log(f"<decodeJson>resourceName={resourceName}" )
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
    log( "</decodeJson>")
    return result

## -- get_metadata_from_resource_id -----------------------------------------
def get_metadata_from_resource_id( resourceId ):
    region = os.getenv("TF_VAR_region")
    customized_url_source = "https://objectstorage."+region+".oraclecloud.com" + resourceId
    return get_upload_metadata( customized_url_source )

## -- has_non_latin1 --------------------------------------------------------
def has_non_latin1(input_string):
    return not all(ord(char) < 255 for char in input_string)

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


## -- upload_file -----------------------------------------------------------

def upload_file( value, namespace_name, bucket_name, object_name, file_path, content_type, metadata ):
        os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
        upload_manager = oci.object_storage.UploadManager(os_client, max_parallel_uploads=10)
        upload_manager.upload_file(namespace_name=namespace_name, bucket_name=bucket_name, object_name=object_name, file_path=file_path, part_size=2 * MEBIBYTE, content_type=content_type, metadata=metadata)
        log( "Uploaded "+object_name, content_type )
        shared_db.insertDoc( value, file_path, content_type )

## -- upload_agent_bucket ---------------------------------------------------

def upload_agent_bucket(value, content=None, path=None):

    log( "<upload_agent_bucket>")
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

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=file_name, part_size=2 * MEBIBYTE, content_type=contentType, metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<upload_agent_bucket> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)     
    log( "</upload_agent_bucket>")                      

## -- genai_agent_datasource_ingest -----------------------------------------

def genai_agent_datasource_ingest():

    log( "<genai_agent_datasource_ingest>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    datasourceId = os.getenv("TF_VAR_agent_datasource_ocid")
    name = "AUTO_INGESTION_" + datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    log( "ingest_job="+name )
    genai_agent_client = oci.generative_ai_agent.GenerativeAiAgentClient(config = {}, signer=signer)    
    genai_agent_client.create_data_ingestion_job(
        create_data_ingestion_job_details=oci.generative_ai_agent.models.CreateDataIngestionJobDetails(
		    data_source_id=datasourceId,
		    compartment_id=compartmentId,
		    display_name=name,
		    description=name
        ))
    log( "</genai_agent_datasource_ingest>")             

## -- libreoffice2pdf ------------------------------------------------------------

def libreoffice2pdf(value):
    log( "<libreoffice2pdf>")
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
            log( f"<libreoffice2pdf> pdf found {pdf_file}")
        else:
            raise subprocess.SubprocessError(stderr)
        metadata = get_metadata_from_resource_id( resourceId )
        log( "pdf_file=" + pdf_file )
        log( "metadata=" + str(metadata) )
        log( "resourceGenAI=" + resourceGenAI )
        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=pdf_file, part_size=2 * MEBIBYTE, content_type="application/pdf", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<libreoffice2pdf> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</libreoffice2pdf>")

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
def image2pdf(value, content=None, path=None):
    log( "<image2pdf>")
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

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI, file_path=pdf_file, part_size=2 * MEBIBYTE, content_type="application/pdf", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<image2pdf> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketGenAI, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</image2pdf>")

## -- webp2png -----------------------------------------------------

def webp2png(value, content=None, path=None):
    log( "<webp2png>")
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

        upload_file( value=value, namespace_name=namespace, bucket_name=bucketName, object_name=resourceGenAI, file_path=png_file, part_size=2 * MEBIBYTE, content_type="image/png", metadata=metadata)
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        log( "<webp2png> Delete")
        try: 
            os_client.delete_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceGenAI)
        except:
           log("Exception: Delete failed: " + resourceGenAI)   
    log( "</webp2png>")    
