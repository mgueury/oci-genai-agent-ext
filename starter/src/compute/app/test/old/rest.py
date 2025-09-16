from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS
import file_convert
from file_convert import log
import rag_storage
import shared_langchain
import json

app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['GET','POST'])
def query():
    a = []
    if request.method=='POST':
        type = request.json.get('type')
        question = request.json.get('question')
    else:
        type = request.args.get('type')
        question = request.args.get('question')
    log( "----------------------------------------")
    log( "type: " + str(type))
    log( "question: " + str(question))
    if type=='langchain':
        a = shared_langchain.queryDb( question )
    else:
        try:
            rag_storage.init()
            embed = shared.embedText(question)
            a = rag_storage.queryDb( type, question, embed) 
        finally:
            rag_storage.close()

    response = jsonify(a)
    response.status_code = 200
    return response   

# Replaced by cohere_chat
@app.route('/llama_chat', methods=['POST'])
def llama_chat():
    messages = request.json.get('message')
    result = shared.llama_chat( message )  
    log("Result="+str(result))  
    return json.dumps(result)  

@app.route('/cohere_chat', methods=['POST'])
def cohere_chat():
    message = request.json.get('message')
    chatHistory = request.json.get('chatHistory')
    documents = request.json.get('documents')
    documentPath = request.json.get('documentPath')
    if documentPath is not None:
        rag_storage.init()
        content = rag_storage.getDocByPath( documentPath )
        rag_storage.close()
        documents = [ { "path": documentPath, "snippet": content } ]    
    result = shared.cohere_chat( message, chatHistory, documents )  
    log("Result="+str(result))  
    return json.dumps(result)  

@app.route('/info')
def info():
    return "Python - Flask - PSQL"          


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

