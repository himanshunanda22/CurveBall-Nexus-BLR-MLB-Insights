from google.cloud import aiplatform
import glob
import os
import re
from llama_index.core import (
    StorageContext,
    Settings,
    VectorStoreIndex,
    SimpleDirectoryReader,
)
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    MetadataFilter,
    FilterOperator,
)
from llama_index.llms.vertex import Vertex
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.vector_stores.vertexaivectorsearch import VertexAIVectorStore
import os
from google.oauth2 import service_account
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DataProcessor:
    """
    A class for processing and ingesting data from text files into a Vertex AI Vector Search index.
    """
    def __init__(self, directory_path, db_path="first-test", collection_name="Baseball-historical-events", model_name="textembedding-gecko@003"):
        """
        Initializes the DataProcessor.

        Args:
            directory_path (str): Path to the directory containing the text files.
            db_path (str, optional): Path to the ChromaDB database (not used in this version with Vertex AI). Defaults to "first-test".
            collection_name (str, optional): Name of the collection (not used in this version with Vertex AI). Defaults to "Baseball-historical-events".
            model_name (str, optional): Name of the embedding model. Defaults to "textembedding-gecko@003".
        """
        self.directory_path = directory_path
        self.PROJECT_ID = os.getenv("PROJECT_ID")
        self.REGION = os.getenv("REGION")
        self.GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
        self.GCS_BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}"
        self.VS_DIMENSIONS = 768  # Dimension of the embeddings - Consider making this configurable if different models are used.
        self.VS_INDEX_NAME = os.getenv("VS_INDEX_NAME") # Name of the Vertex AI Vector Search index
        self.VS_INDEX_ENDPOINT_NAME = os.getenv("VS_INDEX_ENDPOINT_NAME") # Name of the Vertex AI Vector Search index endpoint
        self.INDEX_ID = os.getenv("INDEX_ID")  # Define as instance variable
        self.ENDPOINT_ID = os.getenv("ENDPOINT_ID")  # Define as instance variable
        self.MODEL_NAME = model_name
        aiplatform.init(project=self.PROJECT_ID, location=self.REGION) # Initialize Vertex AI SDK
        self.vs_index = aiplatform.MatchingEngineIndex(index_name=self.INDEX_ID) # Retrieve the index by its name.
        self.vs_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name= self.ENDPOINT_ID) # Retrieve the endpoint by its name.

        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    def extract_text_from_json_string(self, json_string):
        """
        Extracts the relevant information from the JSON-like string, specifically focusing on baseball-related events.

        Args:
            json_string (str): The input string containing the JSON-like data.

        Returns:
            dict: A dictionary containing the extracted text (play_by_play, major_events, etc.) or None if extraction fails.
        """
        json_string = json_string.replace("```json", "").replace("```", "").strip() # Remove backticks and whitespace

        try:
            # Attempt to parse the string as JSON. This is the preferred method.
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError as e:
            logging.warning(f"JSONDecodeError: {e}. Attempting regex extraction as fallback.")

            # If JSON parsing fails (due to malformed JSON), use regex as a fallback.
            pattern = r'"play_by_play": "(.*?)".*"major_events": "(.*?)".*"is_major": "(.*?)".*"homerun": "(.*?)".*"out": "(.*?)".*"strategies": "(.*?)"'
            match = re.search(pattern, json_string, re.DOTALL)
            if match:
                return {
                    "play_by_play": match.group(1).strip(),
                    "major_events": match.group(2).strip(),
                    "is_major": match.group(3).strip(),
                    "homerun": match.group(4).strip(),
                    "out": match.group(5).strip(),
                    "strategies": match.group(6).strip(),
                }
            else:
                logging.warning("Regex extraction failed. No data extracted.")
                return None

    def extract_segment_number(self, filename):
        """Extracts the numerical segment number from the filename for sorting purposes."""
        match = re.search(r'segment_(\d+)\.txt', filename)
        if match:
            return int(match.group(1))
        return float('inf') # Puts files that don't match at the end

    def load_and_process_data(self):
        """
        Loads data from text files in the specified directory, processes it, and prepares it for ingestion.

        Returns:
            list: A list of dictionaries, where each dictionary contains the processed data from a file, or None in case of error.
        """
        records=[] # Stores processed records
        time=0  #Keeps track of the time in the game

        try:
            # Sort the files based on the segment number in their filename.
            files = sorted([entry.path for entry in os.scandir(self.directory_path) if entry.is_file()], key=self.extract_segment_number)
            if not files:
                logging.warning(f"No files found in directory: {self.directory_path}")
                return None

            for filename in files:
                logging.info(f"Processing file: {filename}")
                try:
                    with open(filename, 'r') as f:
                        file_content = f.read()

                        processed = self.extract_text_from_json_string(file_content) #Extracts information from the file
                        if processed:
                            dt = {} #Store all the information and metadata associated with it for a single segment

                            time = time + 30  #Increment time by 30 seconds
                            description_parts = [processed["play_by_play"]] #Start building the description
                            if processed["major_events"]:
                                description_parts.append(f'Major_events: {processed["major_events"]}')  # Add major events if available
                            if processed["strategies"]:
                                description_parts.append(f'Strategies in the game: {processed["strategies"]}') #Add game strategies if available
                            description_parts.append(f'time: {time}t') # Append the time
                            dt["description"] = "\n".join(description_parts) #Join all parts of the description

                            dt["time"] = time  #Stores the current time
                            dt["filename"] = filename  #Stores the filename for the data segment
                            dt["is_major"] = processed["is_major"] #Records whether a major event occured in this segment
                            dt["homerun"] = processed["homerun"] #Records whether a home run occured in this segment
                            dt["out"] = processed["out"] #Records whether an out occured in this segment
                            records.append(dt) #Append this record to the overall list of records


                        else:
                            logging.warning(f"No text to process in file: {filename}")

                except UnicodeDecodeError:
                    logging.error(f"UnicodeDecodeError: Unable to decode file content in {filename}.  Skipping file.")
                except Exception as e:
                    logging.exception(f"An error occurred while processing {filename}: {e}") # Use exception to log the whole stack trace

            return records
        except FileNotFoundError:
            logging.error(f"FileNotFoundError: Directory not found: {self.directory_path}")
            return None
        except Exception as e:
            logging.exception(f"An error occurred: {e}")
            return None

    def ingest_data(self):
        """
        Ingests the processed data into the Vertex AI Vector Search index.
        """
        records = self.load_and_process_data()

        if records:
            #Initialize the Vertex AI Vector Store
            vector_store = VertexAIVectorStore(project_id=self.PROJECT_ID,region=self.REGION,index_id=self.vs_index.resource_name,endpoint_id=self.vs_endpoint.resource_name,gcs_bucket_name=self.GCS_BUCKET_NAME)
            storage_context = StorageContext.from_defaults(vector_store=vector_store) #Create storage context
            key_path = "1.json" #Service account key file

            try:
                # Load the credentials from the key file
                credentials = service_account.Credentials.from_service_account_file(key_path)
                # configure embedding model
                embed_model = VertexTextEmbedding(model_name=self.MODEL_NAME,project=self.PROJECT_ID,location=self.REGION,credentials=credentials) # initialize the embeddings model
                Settings.embed_model = embed_model #Set the default embeddings model in LlamaIndex
            except Exception as e:
                logging.error(f"Error loading credentials or configuring embedding model: {e}")
                return


            nodes = []
            for record in records:
                text = record.pop("description") #Extract the text to be embedded
                try:
                    embedding = embed_model.get_text_embedding(text) #Generate embeddings
                except Exception as e:
                     logging.error(f"Error generating embedding for text: {text}. Skipping record. Error: {e}")
                     continue

                metadata = {**record} #Stores the metadata
                print(text)
                print(metadata)

                nodes.append(TextNode(text=text, embedding=embedding, metadata=metadata)) #Create the text nodes that will be added

            try:
                vector_store.add(nodes) # Add the nodes to the Vertex AI Vector Search Index
                logging.info("Data ingested successfully!")
            except Exception as e:
                logging.error(f"Error adding nodes to vector store: {e}")


        else:
            logging.warning("Data processing failed. No data ingested.")