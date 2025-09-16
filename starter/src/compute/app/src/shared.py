import os
import json
import requests
from datetime import datetime
import oci
import pathlib
import pprint

# -- globals ----------------------------------------------------------------

# OCI Signer
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

# Log
log_file_name = None

# DB Env
db_env = None

# Create Log directory
LOG_DIR = '/tmp/app_log'
if os.path.isdir(LOG_DIR) == False:
    os.mkdir(LOG_DIR) 

UNIQUE_ID = "ID"

## -- log_write_in_file -------------------------------------------------------------------
# Write logs in a file also 

def log_write_in_file( file_name ): 
   global log_file_name               
   log_file_name = file_name

## -- log -------------------------------------------------------------------

def log(s):
   global log_file_name
   dt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
   s2 = "["+dt+"] "+ str(s)
   print( s2, flush=True)
   if log_file_name:
       with open(log_file_name, "a", encoding="utf-8") as log_file:
           log_file.write(s2+'\n')       

## -- log_in_file -----------------------------------------------------------
# Log a full file 

def log_in_file(prefix, value):
    global UNIQUE_ID
    # Create Log directory
    if os.path.isdir(LOG_DIR) == False:
        os.mkdir(LOG_DIR)     
    filename = LOG_DIR+"/"+prefix+"_"+UNIQUE_ID+".txt"
    with open(filename, "w", encoding="utf-8") as text_file:
        text_file.write(value)
    log("<log_in_file>" +filename )  

## -- dictString ------------------------------------------------------------

def dictString(d,key):
   return d.get(key, "-")
   
## -- dictInt ------------------------------------------------------------

def dictInt(d,key):
   return int(float(d.get(key, 0)))
   
## -- summarizeContent ------------------------------------------------------

def summarizeContent(value,content):
    log( "<summarizeContent>")
    global signer
    compartmentId = value["data"]["compartmentId"]
    region = os.getenv("TF_VAR_region")    
    endpoint = 'https://inference.generativeai.'+region+'.oci.oraclecloud.com/20231130/actions/chat'
    # Avoid Limit of 4096 Tokens
    if len(content) > 12000:
        log( "Truncating to 12000 characters")
        content = content[:12000]

    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": os.getenv("TF_VAR_genai_cohere_model"),
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
        return dictString(dictString(j,"chatResponse"),"text") 
    except requests.exceptions.HTTPError as err:
        log("\u270B Exception: summarizeContent") 
        log(err.response.status_code)
        log(err.response.text)
        return "-"   
    
## -- embedText -------------------------------------------------------------

# Ideally all vectors should be created in one call
def embedText(c):
    global signer
    log( "<embedText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    region = os.getenv("TF_VAR_region")
    endpoint = 'https://inference.generativeai.'+region+'.oci.oraclecloud.com/20231130/actions/embedText'
    body = {
        "inputs" : [ c ],
        "servingMode" : {
            "servingType" : "ON_DEMAND",
            "modelId" : os.getenv("TF_VAR_genai_embed_model")
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

## -- llama_chat -----------------------------------------------------------

def llama_chat(prompt):
    global signer
    log( "<llama_chat>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    region = os.getenv("TF_VAR_region")    
    endpoint = 'https://inference.generativeai.'+region+'.oci.oraclecloud.com/20231130/actions/chat'
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": os.getenv("TF_VAR_genai_meta_model"),
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
    log( "</llama_chat>")
    return s

## -- cohere_chat -----------------------------------------------------------

def cohere_chat(prompt, chatHistory, documents):
    global signer
    log( "<cohere_chat>")
    region = os.getenv("TF_VAR_region")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.'+region+'.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": os.getenv("TF_VAR_genai_cohere_model"),
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": os.getenv("TF_VAR_genai_cohere_model"),
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
    
## -- genai_agent_datasource_ingest -----------------------------------------

def genai_agent_datasource_ingest():

    log( "<genai_agent_datasource_ingest>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    datasourceId = os.getenv("TF_VAR_agent_datasource_ocid")
    if datasourceId:
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


## -- genai_agent_get_session -------------------------------------------

def genai_agent_get_session():

    log( "<genai_agent_get_session>")
    agent_endpoint_ocid = os.getenv("TF_VAR_agent_endpoint_ocid")
    region=os.getenv("TF_VAR_region")
    genai_agent_runtime_client = oci.generative_ai_agent_runtime.GenerativeAiAgentRuntimeClient(
        config = {}, 
        signer=signer,
        service_endpoint="https://agent-runtime.generativeai."+region+".oci.oraclecloud.com",
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )    
    # Create session
    create_session_details = oci.generative_ai_agent_runtime.models.CreateSessionDetails(
        display_name="session", description="description"
    )
    create_session_response = genai_agent_runtime_client.create_session(create_session_details, agent_endpoint_ocid)

    log( "</genai_agent_get_session>")  
    return create_session_response.data.id

## -- genai_agent_chat ------------------------------------------------------

def genai_agent_chat( session_id, question ):

    log( "<genai_agent_chat>")
    agent_endpoint_ocid = os.getenv("TF_VAR_agent_endpoint_ocid")
    region=os.getenv("TF_VAR_region")
    genai_agent_runtime_client = oci.generative_ai_agent_runtime.GenerativeAiAgentRuntimeClient(
        config = {}, 
        signer=signer,
        service_endpoint="https://agent-runtime.generativeai."+region+".oci.oraclecloud.com",
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )    

    chat_details = oci.generative_ai_agent_runtime.models.ChatDetails(
        user_message=str(question), should_stream=False, session_id=session_id # You can set this to True for streaming responses
    )
    execute_session_response = genai_agent_runtime_client.chat(agent_endpoint_ocid, chat_details)

    if execute_session_response.status == 200:
        if execute_session_response.data.message:
            # response_content = execute_session_response.data.message.content
            log(pprint.pformat( execute_session_response ))            
            return execute_session_response.data
            # Text -> response_content = execute_session_response.data.message.content.text
   
    return None

## -- getFileExtension ------------------------------------------------------

def getFileExtension(resourceName):
    lowerResourceName = resourceName.lower()
    return pathlib.Path(lowerResourceName).suffix

## -- delete_bucket_folder --------------------------------------------------

def delete_bucket_folder(namespace, bucketName, folder):
    log( "<delete_bucket_folder> "+folder)
    try:
        os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)    
        response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketName, prefix=folder, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
        for object_file in response.data.objects:
            f = object_file.name
            log( "<delete_bucket_folder> Deleting: " + f )
            os_client.delete_object( namespace_name=namespace, bucket_name=bucketName, object_name=f )
            log( "<delete_bucket_folder> Deleted: " + f )
    except:
        log("\u270B <delete_bucket_folder> Exception: delete_bucket_folder") 
        log(traceback.format_exc())            
    log( "</delete_bucket_folder>" )    
