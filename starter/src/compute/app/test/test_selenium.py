# Test_selenium
import sys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json
import os
import base64
import xmltodict
from datetime import datetime

LOG_DIR="/tmp/app_log"

## -- log ------------------------------------------------------------------

def log(s):
   dt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
   print( "["+dt+"] "+ str(s), flush=True)

## -- loop_sitemap_xml ---------------------------------------------------
def loop_sitemap_xml(sitemap):
    log( "<loop_sitemap>" )
    f = open(sitemap, "rb")
    raw = xmltodict.parse(f.read())
    driver = chrome_webdriver()
    log( "after driver" )
    if raw.get("sitemapindex"):
        for sitemap in raw["sitemapindex"]["sitemap"]:
            log( f"<loop_sitemap> Not supported: {sitemap}" )

    if raw.get("urlset"):
        for url in raw["urlset"]["url"]:
            loc = url["loc"]
            filename = loc.replace('/', '__')
            log( f"<loop_sitemap> {url}" )
            chrome_download_url_as_pdf( driver, loc, LOG_DIR + '/' + filename)
    driver.quit()

## -- chrome_webdriver ---------------------------------------------------
def chrome_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
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
    driver.implicitly_wait(5) 
    try:
        element_present = EC.presence_of_element_located((By.TAG_NAME, 'body')) # Example: wait for the <body> tag
        WebDriverWait(driver, 20).until(element_present) # Wait up to 20 seconds
    except Exception as e:
        print(f"Error waiting for element: {e}")    

    print_options = {
        "pageRanges": "1-1",  # Print all pages (you can customize this)
        "marginsType": 1,      # Set margins (0 = default, 1 = no margins, 2 = minimal margins)
        "printBackground": True, # Print background graphics
    }
    params = {'behavior': 'default', 'downloadPath': os.getcwd()} # Set the download directory to current working directory
    driver.execute_cdp_cmd('Page.setDownloadBehavior', params) # Set the download path for the PDF
    result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
    pdf_data = result['data']
    with open(output_filename, "wb") as f:
        f.write(bytes(base64.b64decode(pdf_data)))
    log(f"<chrome_download_url_as_pdf> Saved {output_filename}")   

## -- sitemap ------------------------------------------------------------------
def convertChromeSelenium2Pdf(value):

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
        upload_manager = oci.object_storage.UploadManager(os_client, max_parallel_uploads=10)            

        resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
        file_name = LOG_DIR+"/"+UNIQUE_ID+".sitemap"
        with open(file_name, 'wb') as f:
            for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)

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
                        chrome_download_url_as_pdf( driver, full_uri, LOG_DIR+'/'+pdf_path)
    
                        metadata = {'customized_url_source': full_uri}

                        # Upload to object storage as "site/"+pdf_path
                        upload_manager.upload_file(namespace_name=namespace, bucket_name=bucketGenAI, object_name=prefix+"/"+pdf_path, file_path=LOG_DIR+"/"+pdf_path, part_size=2 * MEBIBYTE, content_type='application/pdf', metadata=metadata)
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
        driver.quit()            
    log( "</sitemap>")

if __name__ == '__main__':
    loop_sitemap_xml( "sitemap.xml")
    # driver = chrome_webdriver()
    # chrome_download_url_as_pdf( driver, "https://google.com", "google.pdf")
    # chrome_download_url_as_pdf( driver, "https://www.oracle.com", "oracle.pdf")
    # driver.quit()



