import oci
import os
import shared_oci
from pdf2image import convert_from_path
from PIL import Image, ImageDraw 

# ---------------------------------------------------------------------------
def remove_entities(anonym_pdf_file, j):
    images = convert_from_path(anonym_pdf_file)
    page_count = len(images)
  
    pages_boxes = entities( images, j ) 
    for idx, image in enumerate(images):
        # images[idx] = images[idx].convert('RGB')
        draw_boxes(images[idx], pages_boxes[idx])
    pdf_file = anonym_pdf_file.replace(".anonym.pdf", ".pdf")    
    shared_oci.save_image_as_pdf( pdf_file, images )  
    shared_oci.log( "</remove_entities> pdf_file created: "+ pdf_file )
    return pdf_file

# ---------------------------------------------------------------------------
def draw_boxes( image: Image.Image, boxes ):
    for i, (x1, y1, x2, y2, color) in enumerate(boxes):
        img1 = ImageDraw.Draw(image) 
        img1.rectangle( [(x1, y1), (x2, y2)], color )

# ---------------------------------------------------------------------------
def add_box( boxes, p, width, height, text, type ):
    if '\n' in text:
        lines = text.splitlines()
        for line in lines:
            box = get_box( p, width, height, line, type )  
            if box:  
                boxes.append( box )
    else:
        box = get_box( p, width, height, text, type )  
        if box:  
            boxes.append( box )

# ---------------------------------------------------------------------------
def get_box( p, width, height, text, type ):
    shared_oci.log( "<get_box>" + text)
    if type=="PERSON":
        color = "#330"
    elif type=="DATETIME":
        return None 
    elif type=="LOCATION":
        color = "#030"
    elif type=="EMAIL":
        color = "#300"
    elif type=="ORGANIZATION":
        color = "#033"
    elif type=="QUANTITY":
        return None       
    else:
        color = "#000"
    for line in p.get("lines"):
        line_text = line.get("text")
        if text in line_text:
            if line.get("boxed"):
                shared_oci.log( "<get_box> WARNING: already boxed. Continuing to search." )         
            else:  
               c = line.get("confidence")
               v = line.get("boundingPolygon").get("normalizedVertices")
               box= ( int(v[0].get("x")*width), int(v[0].get("y")*height), int(v[2].get("x")*width), int(v[3].get("y")*height), color )
               shared_oci.log( "<get_box>text found: " + text + " / " + str(c) + " / " + str(box)   )                         
               line["boxed"] = True
               return box
    shared_oci.log( "<get_box> ERROR: text not found: " + text )         
    return None         

# ---------------------------------------------------------------------------
def entities( images, j ):
    shared_oci.log( "<entities>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    
    documents = []
    # Parse the output of document understanding
    for p in j.get("pages"):
        pageNumber = p.get("pageNumber")
        text = ""
        for l in p.get("lines"):
            text += l.get("text") + "\n"
        doc = {
            "languageCode": "auto",
            "key": str(pageNumber),
            "text": text            
        }
        documents.append( doc )
    ai_client = oci.ai_language.AIServiceLanguageClient(config = {}, signer=shared_oci.signer)  
    details = {
        "documents": documents,
        "compartmentId": compartmentId
    }
    response = ai_client.batch_detect_language_entities( details )
    shared_oci.log_in_file( "entities", str(response.data) )

    # Calculate the boxes
    pages_boxes = []
    
    for p in j.get("pages"):
        pageNumber = str(p.get("pageNumber"))
        shared_oci.log( "<entities> pageNumber " + pageNumber )
        image = images [int(pageNumber)-1]
        width, height = image.size
        boxes = []
        for doc in response.data.documents:
            shared_oci.log( "<entities> doc.key " + doc.key )
            if doc.key==pageNumber:
                for entity in doc.entities:
                    add_box( boxes, p, width, height, entity.text, entity.type )  
        pages_boxes.append( boxes )    
    shared_oci.log( "</entities> ")
    return pages_boxes


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    file_name = "anonymize/resume.pdf"
    images = convert_from_path(file_name)
    print( "Number of pages" + str(len(images)) )
  
    for image in images:
        width, height = image.size
        print( type(Image) )
        print( "Width="+ str(width) + " / Height="+ str(height) )
        boxes = [
            (0, 0, 10, 10),
            (width/2, height/2, 10, 10)
        ]
        draw_boxes( image, boxes)
    shared_oci.save_image_as_pdf( "anonymize/temp.pdf", images)
