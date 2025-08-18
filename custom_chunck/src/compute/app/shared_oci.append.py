import csv
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

## -- run_crawler ------------------------------------------------------------
def run_crawler(url):
    """
    Executes the spider and, upon completion, reads and
    prints the contents of the generated links.csv file.
    """
    # Define the command to run the Spider.
    # The command assumes you are running this script from the
    # root directory of the project (where scrapy.cfg is located).
    crawler_command = ['./crawler.sh', url]
    
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

## -- crawler ------------------------------------------------------------------
def crawler(value):
    log( "<crawler>")
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
                                filename = filename[len(CRAWLER_DIR)+1:]
                                print("-" * 50)
                                print(f"URL: {url} - Filename: {filename}")
                                metadata=  {'customized_url_source': url, 'gaas-metadata-filtering-field-folder': folder }    
                                upload_file(value=value, namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+filename, file_path=CRAWLER_DIR+"/"+filename, content_type='text/html', metadata=metadata)
                                fileList.append(filename)
                        
                    except Exception as e:
                        log("<crawler>Error parsing line: "+line+" in "+resourceName)
                        log("<crawler>Exception:" + str(e))

            # Check if there are file that are in the folder and not in the crawler
            response = os_client.list_objects( namespace_name=namespace, bucket_name=bucketGenAI, prefix=prefix, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY, limit=1000 )
            for object_file in response.data.objects:
                f = object_file.name
                if f in fileList:
                    fileList.remove(f)
                else: 
                    log( "<crawler>Deleting: " + f )
                    os_client.delete_object( namespace_name=namespace, bucket_name=bucketGenAI, object_name=f )
                    log( "<crawler>Deleted: " + f )

        except FileNotFoundError as e:
            log("<crawler>Error: File not found= "+file_name)
        except Exception as e:
            log("<crawler>An unexpected error occurred: " + str(e))     
    log( "</crawler>")

