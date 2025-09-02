# Import
import oci
import os
import json 
import time
import traceback
import shared
from shared import log
from shared import log_in_file
import shared_db
import document

from datetime import datetime
from base64 import b64decode

## -- stream_cursor --------------------------------------------------------

def stream_cursor(sc, sid, group_name, instance_name):
    log("<stream_cursor>")
    cursor_details = oci.streaming.models.CreateGroupCursorDetails(group_name=group_name, instance_name=instance_name,
                                                                   type=oci.streaming.models.
                                                                   CreateGroupCursorDetails.TYPE_TRIM_HORIZON,
                                                                   commit_on_get=True)
    response = sc.create_group_cursor(sid, cursor_details)
    return response.data.value

## -- stream_loop --------------------------------------------------------

def stream_loop(client, stream_id, initial_cursor):
    updateCount = 0
    cursor = initial_cursor
    while True:
        get_response = client.get_messages(stream_id, cursor, limit=10)
        # No messages to process. return.
        if not get_response.data:
            document.updateCount( updateCount )
            return

        # Process the messages
        log("<stream_loop> Read {} messages".format(len(get_response.data)))
        updateCount += len(get_response.data)
        for message in get_response.data:
            try:
                log("--------------------------------------------------------------" )
                if message.key is None:
                    key = "Null"
                else:
                    key = b64decode(message.key.encode()).decode()
                json_value = b64decode(message.value.encode()).decode(); 
                log(json_value)
                shared.UNIQUE_ID = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
                log_in_file("stream", json_value)
                value = json.loads(json_value)
                document.eventDocument(value)
            except:
                log("Exception: stream_loop") 
                log(traceback.format_exc())
        log("<stream_loop> Processed {} messages".format(len(get_response.data)))        
            
        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]

## -- main ------------------------------------------------------------------

ociMessageEndpoint = os.getenv('STREAM_MESSAGE_ENDPOINT')
ociStreamOcid = os.getenv('STREAM_OCID')

while True:
    stream_client = oci.streaming.StreamClient(config = {}, service_endpoint=ociMessageEndpoint, signer=shared.signer)
    try:
        while True:
            shared_db.initDbConn()
            group_cursor = stream_cursor(stream_client, ociStreamOcid, "app-group", "app-instance-1")
            stream_loop(stream_client, ociStreamOcid, group_cursor)
            shared_db.closeDbConn()
            time.sleep(30)
    except:
        log("----------------------------------------------------------------------------")
        log("<main>Exception in streamloop")
        log(traceback.format_exc())
        # Resetting Stream - This is needed when you have the cursor that is too old. 
        # Error: 400 - The cursor is outside the retention period and is now invalid.
        # Some message will be lost. Trim_horizon take the oldest one.
        update_group_response = stream_client.update_group(
            stream_id=ociStreamOcid,
            group_name="app-group",
            update_group_details=oci.streaming.models.UpdateGroupDetails(type="TRIM_HORIZON"))
