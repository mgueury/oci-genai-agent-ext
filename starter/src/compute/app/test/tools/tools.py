from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from langchain_community.tools.tavily_search import TavilySearchResults
import logging

app = FastAPI()
logging.basicConfig( format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

#----------------------------------------------------------------------------

@app.get("/hello")
def hello():
    """
    Hello World.

    Returns:
        Hello World.
    """
    return ("Hello World")

# curl http://localhost:8080/hello
#
