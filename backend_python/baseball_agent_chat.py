import os
from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
import json
from datetime import datetime, timedelta
import time
from google import genai
from google.genai import types
from textwrap import dedent
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid
from crewai.tools import BaseTool
from google.cloud import aiplatform
from google.oauth2 import service_account
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from crewai import LLM
from llama_index.core import (
    StorageContext,
    Settings,
    VectorStoreIndex,
)
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    MetadataFilter,
    FilterOperator,
)
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.vector_stores.vertexaivectorsearch import VertexAIVectorStore

load_dotenv()


# --- Configuration ---
PROJECT_ID = os.environ["PROJECT_ID"]  # Google Cloud project ID
REGION = os.environ["REGION"]  # Region for Vertex AI services
GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]  # Google Cloud Storage bucket name
GCS_BUCKET_URI = f"gs://{GCS_BUCKET_NAME}"  # Google Cloud Storage bucket URI
VS_DIMENSIONS = 768  # Vector dimensions for Vertex AI Vector Search

VS_INDEX_NAME = os.environ["VS_INDEX_NAME"]  # Name of the Vertex AI Vector Search index
VS_INDEX_ENDPOINT_NAME = os.environ["VS_INDEX_ENDPOINT_NAME"]  # Name of the Vertex AI Vector Search index endpoint

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]  # API key for Google services (Gemini, etc.)
MODEL_ID = os.environ["MODEL_ID"]  # Model ID for Gemini
INDEX_ID = os.environ["INDEX_ID"]  # ID of the Vertex AI Matching Engine Index
ENDPOINT_ID = os.environ["ENDPOINT_ID"]  # ID of the Vertex AI Matching Engine Index Endpoint


# Initialize tools
search_tool = SerperDevTool()  # Tool for searching the web
scrape_web = ScrapeWebsiteTool()  # Tool for scraping website content
SYSTEM_PROMPT = "When given a video and a query, provide answer to the user query based on the provided video"  # System Prompt for analyzing the video
print("Connecting to Vertex AI Vector Search...")

# Initialize Vertex AI and Vector Search
try:
    aiplatform.init(project=PROJECT_ID, location=REGION)  # Initialize Vertex AI
    vertex_ai_index = aiplatform.MatchingEngineIndex(index_name=INDEX_ID)  # Load the Vertex AI Matching Engine Index
    vertex_ai_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=ENDPOINT_ID)  # Load the Vertex AI Matching Engine Index Endpoint
    vector_store = VertexAIVectorStore(project_id=PROJECT_ID, region=REGION, index_id=vertex_ai_index.resource_name, endpoint_id=vertex_ai_endpoint.resource_name, gcs_bucket_name=GCS_BUCKET_NAME)  # Initialize the Vertex AI Vector Store
    storage_context = StorageContext.from_defaults(vector_store=vector_store)  # Initialize the storage context for LlamaIndex

    # Load credentials
    key_path = "1.json"  # Path to Service Account
    credentials = service_account.Credentials.from_service_account_file(key_path)  # Load credentials from service account file

    # Configure embedding model
    embed_model = VertexTextEmbedding(model_name="textembedding-gecko@003", project=PROJECT_ID, location="us-central1", credentials=credentials)  # Initialize the Vertex AI Text Embedding model
    Settings.embed_model = embed_model  # Set the embedding model for LlamaIndex

    # Initialize index
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)  # Load the LlamaIndex Vector Store Index
    print("Vertex AI Vector Search connected.")
except Exception as e:
    print(f"Error connecting to Vertex AI Vector Search: {e}")
    raise


# --- Data Model Definitions ---
class QueryAnalysis(BaseModel):
    """Represents the analysis of a user query."""
    type: str  # Type of query (realtime, historical, search)
    time_reference: str  # Time reference extracted from query (e.g., "7th inning"), or None if not applicable
    optimized_query: str  # Optimized query string


class VectorSearchFilter(BaseModel):
    """Represents a filter for vector search."""
    key: str  # Metadata key to filter on
    value: int  # Value to filter for
    operator: str  # Comparison operator (e.g., "LT", "GT", "EQ")


class ModifiedQuery(BaseModel):
    """Represents a modified query for vector search."""
    modified_query: str  # Modified query string optimized for vector search

class GeminiVisionOutput(BaseModel):
    """Represents Gemini Vision output."""
    query: str  # User's query
    video: str  # Video analyzed
    response: str  # Gemini Vision's response

class HistoricalOutput(BaseModel):
    """Represents historical output."""
    answer: str  # Answer extracted from historical data
    query: str  # User's query
    citations: list  # List of citations

class SearchOutput(BaseModel):
    """Represents search output."""
    answer: str  # Answer from web search
    citations: str  # Citations for the answer

# --- Baseball Analysis Service Class ---
class BaseballAnalysisService():
    def __init__(self):
        """Initializes the Baseball Analysis Service with LLM, Vector DB, and agents/tasks."""
        try:
            # Initialize Gemini LLM
            self.llm = LLM(model="gemini/gemini-2.0-flash-exp", api_key=os.environ["GEMINI_API_KEY"])
            self.client = genai.Client(api_key=GOOGLE_API_KEY)

            self.init_agents()
            self.init_tasks()
        except Exception as e:
            print(f"Error initializing BaseballAnalysisService: {e}")
            raise

    def init_agents(self):
        """Initializes and configures the agents with their respective roles and tools."""

        @tool()
        def analyze_video(query: str, video: str) -> str:
            """
            Analyzes a given video using the Gemini Vision model.

            Args:
                query (str): The question to be passed as a query to the Gemini Vision model.
                video (str): The video that needs to be uploaded and analyzed.

            Returns:
                str: The Gemini response.
            """
            print("\nAnalyzing video with Gemini Vision...")
            print(f"  Query: {query}")
            print(f"  Video: {video}")

            try:
                segment_name = video.split("/")[-1]
                with open("sync.json", "r") as f:
                    sync_data = json.load(f)
                index_number = sync_data[segment_name]
                with open("cache/past_game_summary.json", "r") as f:
                    past_game_summary = json.load(f)

                previous_context_summary = past_game_summary.get(index_number, None)
                previous_context_summary_prompt = f"""
                Here is the summary of whatever has happened so far and so consider this as the context as reference and also by analyzing the video answer the provided  query :

                Previous Context:
                {previous_context_summary}

                Analyze the video and provide the answer to the query.
                """
                system_prompt = SYSTEM_PROMPT + "\n"
                system_prompt += previous_context_summary_prompt
                file_upload = self.client.files.upload(path=video)
                print("processing")
                while file_upload.state == "PROCESSING":
                    time.sleep(10)
                    file_upload = self.client.files.get(name=file_upload.name)

                if file_upload.state == "FAILED":
                    print("  File upload failed.")
                    return None

                prompt = query

                print("  Calling Gemini Vision API...")
                print(system_prompt)
                response = self.client.models.generate_content(
                    model=MODEL_ID,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_uri(file_uri=file_upload.uri, mime_type=file_upload.mime_type)]
                        ),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.0,
                    ),
                )
                print("  Gemini Vision analysis complete.")
                return response.text
            except Exception as e:
                print(f"Error analyzing video: {e}")
                return None

        # Agent Definitions
        self.query_optimization_agent = Agent(
            role="Query Optimization and Analysis Expert",
            goal="Optimize user queries for the best response and determine if they are real-time or historical, extracting any time references.",
            backstory="A highly skilled expert in both understanding and optimizing user queries. This agent is adept at discerning the nature of a user's information request (real-time vs. historical) and identifying time-related components within the query. Furthermore, they utilize their optimization expertise to rephrase queries in a manner that maximizes the quality of the response.",
            llm=self.llm
        )

        self.realtime_analysis_agent = Agent(
            role="Real-Time Analyst",
            goal="You are an Expert at answering the user query against a given video by making use of 'analyze_video' tool.",
            backstory="An expert at providing answer to a given user query against a real-time video feeds.",
            tools=[analyze_video],
            llm=self.llm
        )

        self.query_optimizer_agent = Agent(
            role="Baseball Query and Metadatafilter",
            goal="You are an expert at converting the user query to a query that can fetch better chunks from vector database and also at extracting metadata from the given query",
            backstory="An expert at optimizing query and extracting meta data from the query",
            llm=self.llm
        )

        self.retrieval_agent = Agent(
            role="Baseball RAG Analyst",
            goal="Provide answers to user questions by retrieving information from vector db transcripts using RAG.",
            backstory="An expert at using retrieval augmented generation to analyze baseball game transcripts.",
            llm=self.llm
        )

        self.mlb_information_agent = Agent(
            role="MLB Information Gatherer",
            goal="Gather all possible information related to the user's MLB query from various sources, including web searches and website content. Provide a comprehensive collection of relevant data.",
            backstory="""An expert MLB researcher specializing in gathering detailed and comprehensive information on any topic related to Major League Baseball. This agent excels at scouring the internet, identifying valuable sources, and extracting key details from websites and documents. Their primary focus is on information retrieval, ensuring all relevant data is captured, rather than analysis or interpretation.""",
            tools=[search_tool, scrape_web],
            llm=self.llm
        )

    def init_tasks(self):
        """Initializes and configures the tasks for the agents."""

        class VectorDBSearchTool(BaseTool):
            name: str = "search_vector_db"
            description: str = "'search_vector_db' uses this tool to Searches the vector database using a given query and filters. Args: query (str): The query to be passed to the vector DB. filters (dict): The filter expression to be passed to the vector DB. Returns: str: The most relevant chunks to the given query."

            def _run(self, query: str, filters: dict) -> str:
                """Runs the VectorDB search and returns results."""
                print("\nFetching content from LlamaIndex with retriever...")
                print(f"Filters: {filters}")
                print(f"Query: {query}")
                try:
                    if filters:
                        if filters["key"] == 'time':
                            v = float(filters['value'])
                            print(v)
                            operator_str = filters["operator"]
                            if operator_str == "LT":
                                op = FilterOperator.LT
                            elif operator_str == "GT":
                                op = FilterOperator.GT
                            elif operator_str == "EQ":
                                op = FilterOperator.EQ
                            elif operator_str == "NE":
                                op = FilterOperator.NE
                            elif operator_str == "LE":
                                op = FilterOperator.LE
                            elif operator_str == "GE":
                                op = FilterOperator.GE
                            else:
                                print("Enter a valid operator")
                                return "Invalid operator"

                            metadata_filters = MetadataFilters(filters=[MetadataFilter(key=filters["key"], value=v, operator=op)])
                        else:
                            v = str(filters['value'])
                            print(filters["key"])
                            print(v)
                            metadata_filters = MetadataFilters(filters=[MetadataFilter(key=filters["key"], value=v)])
                    else:
                        metadata_filters = []

                    retriever = index.as_retriever(filters=metadata_filters, similarity_top_k=10)
                    response = retriever.retrieve(query)
                    results = []

                    for row in response:
                        chunk_data = {"id": str(uuid.uuid4()), "text": row.get_text(), "score": row.get_score(), "metadata": row.metadata}
                        print(f"  Text: {row.get_text()}")
                        print(f"  Score: {row.get_score():.3f}")
                        print(f"  Metadata: {row.metadata}")
                        results.append(chunk_data)

                    print(f"  Retrieved {len(results)} chunks.")

                    return json.dumps(results)  # Return results as a JSON string
                except Exception as e:
                    print(f"Error during VectorDB search: {e}")
                    return str({"error": f"Error during VectorDB search: {e}"})

        self.query_analysis_task = Task(
            description=dedent(
                """
            You are an expert sports query analyzer and optimizer. Your task is to analyze a user's query about a sports game and generate two outputs: a JSON object describing the temporal aspect of the query and an optimized version of the query.

            **Analysis:**
            1. Determine if the query requires real-time information (e.g., live updates), historical information (e.g., past events within the current game), or requires a search for general information about a team or player.
            2. Real-time cues include phrases like "right now," "currently," "any updates","in this" and so on.
            3. Historical cues (within the context of the current game) include phrases like "in the 7th inning," "last 3 innings," "20 minutes ago" or other specific times within the current game.
            4. Any query about the past games, general statistics, player information, or anything beyond simple live or historical game data within the current game should be classified as a search.
            5. If the query is historical (within the context of the current game), extract any specific time references (e.g., "7th inning," "last 3 innings," "20 minutes ago").
            6. Represent your analysis as a JSON object with the following keys: "type" and "time_reference". "type" should be either "realtime", "historical", or "search". "time_reference" should be a string representing the extracted time reference, or null if no specific time reference is given.

            **Query Optimization:**
            1. Identify the core request of the user's query (e.g., score, stats, player info).
            2. Identify any ambiguities or vague references in the query (e.g., unclear team, player, or time).
            3. Rewrite the query to be more specific and explicit. Remove ambiguity and ensure the optimized query can be understood by a database or information retrieval system.
            4. Maintain the original user intent while making the query more explicit. If the "type" is "search", phrase the optimized query in a way that would be suitable for a web search.

            **Output:**
            You should output a single JSON object containing both the analysis and the optimized query string. The format of the output should be as follows:
            ```json
            {{
                "type": "realtime" | "historical" | "search",
                "time_reference": "optional time string" | null,
                "optimized_query": "Optimized query string"
                }}


            ```

            **Examples:**

            **Input:**
            Query: "What's the score of the game right now?"

            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "What is the current score of the game?"
                }}
            ```
            **Input:**
            Query: "Any score updates?"

            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "What is the latest score of the game?"
                }}

            ```
            **Input:**
            Query: "How are the Lakers doing?"

            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "What is the current score of the Los Angeles Lakers game, and what are their stats for the current game?"
                }}
            ```
            **Input:**
            Query: "Who scored last in the match?"

            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "Who scored the last goal in the current game?"
                }}
            ```
            **Input:**
            Query: "Show me the highlights from the game"

            **Output:**
            ```json
            {{
                "type": "historical",
                "time_reference": null,
                "optimized_query": "Show the highlights from the current game"
                }}
            ```
            **Input:**
            Query: "What happened 20 minutes ago?"

            **Output:**
            ```json
            {{
                "type": "historical",
                "time_reference": "20 minutes ago",
                "optimized_query": "What were the key events that happened 20 minutes ago within the current game?"
                }}
            ```

            **Input:**
            Query: "What about the game yesterday"

            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for the final scores and statistics from the game that was played yesterday."
                }}
            ```

            **Input:**
            Query: "Are they winning"

            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "Is the team winning in their current match?"
                }}
            ```
            **Input:**
            Query: "Show me Lebron stats"

            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for LeBron James' current game stats and career statistics."
                }}
            ```
            **Input:**
            Query: "Tell me about the history of the Lakers"

            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for the history of the Los Angeles Lakers basketball team."
                }}
            ```
            **Input:**
            Query: "Who is the quarterback for the chiefs?"

            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for the current starting quarterback of the Kansas City Chiefs."
                }}
            ```
            **Input:**
            Query: "What is Stephen Curry's average points this season?"

            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for Stephen Curry's average points per game for the current season."
                }}
            ```
            **Input:**
            Query: "Who is playing right now?"
            **Output:**
            ```json
            {{
                "type": "realtime",
                "time_reference": null,
                "optimized_query": "Which teams are playing in the current matches?"
            }}
            ```

            **Input:**
            Query: "What was the score at the half?"
            **Output:**
            ```json
            {{
                "type": "historical",
                "time_reference": "half",
                "optimized_query": "What was the score at halftime in the current game?"
            }}
            ```

            **Input:**
            Query: "How many home runs did they hit yesterday?"
            **Output:**
            ```json
            {{
                "type": "search",
                "time_reference": null,
                "optimized_query": "Search for the number of home runs hit by the team in the game yesterday."
            }}
            ```
            **Actual Input:**
            Query: {query}
        """
            ),
            expected_output='A JSON object string containing the analysis of the sports game query with keys "type" and "time_reference", and an optimized query string, Example: {{"type": "realtime"|"historical"|"search", "time_reference": "optional time string"|null, "optimized_query": "An optimized query string..."}}',
            agent=self.query_optimization_agent,
            output_json=QueryAnalysis,
        )

        self.realtime_video_analysis_task = Task(
            description=dedent("""
            You are provided with a real-time video feed {video} and a single question {question} related to its content.
            Your goal is to use the 'analyze_video' tool to process the video stream and
            accurately answer the question. Provide the question, the video source, and its corresponding answer
            as a JSON object, without omitting any important details.
            """),
            expected_output=dedent("""
            A JSON object containing the user's question, the video source, and its corresponding answer
            based on real-time video analysis. Ensure the output is valid JSON and has the following structure:

            {{
                "query": "<user's question>",
                "video": "<video source>",
                "response": "<answer from video analysis include only the answer to the user query it should just be a string do not add any extra field and include only the answer>"
            }}
            """),
            agent=self.realtime_analysis_agent,
            output_json=GeminiVisionOutput,
        )

        self.vector_search_filter_task = Task(
            description=dedent("""
                **Task:** Generate Filters for Vector Search

                You are an expert in processing user queries and generating filters for vector database searches, with a focus on time-based and baseball-related information.
                You will receive:
                1. A **user query** describing the information they seek (e.g., "What happened 30 seconds ago?", "When did bunting occur?", "Show me the latest homerun", "since last 20 sec", "Show me major events").
                2. The **current time** as a reference point for calculating durations (e.g., "50 seconds").

                Your goal is to:

                1. Generate the appropriate filter based on whether the query is time related or not or contains the event type information.
                **Filter Logic:**
                A filter is a JSON dictionary with keys "key", "value", and "operator". Time filters use the key `time`.
                Non-time filters use key as a category of events such as `is_major`, `homerun` , `out`. The value for the non-time filters is always a string
                **Time-Based Queries:**
                When the query contains explicit references to time, follow these steps:
                * Always convert time references from both user query and current time to seconds.
                * **"X seconds back" (or "X seconds ago")**: (e.g., "30 seconds back", "5 minutes ago")
                    - Calculate the time difference between the current time and the time mentioned in the user query.
                    - Return a filter like this: {{"key": "time", "value": <time_in_seconds>, "operator": "EQ"}}
                 * **"last X seconds" (or "last Xs")** : (e.g., "last 30 seconds", "last 10 s")
                - Calculate the time difference between the current time and the time mentioned in the user query.
                - Return a filter like this: {{"key": "time", "value": <time_in_seconds>, "operator": "GT"}}
                * **"Exactly X seconds back"**: (e.g., "exactly 40 seconds back", "precisely 1 minute before")
                    - Calculate the time difference.
                    - Return a filter like this: {{"key": "time", "value": <time_in_seconds>, "operator": "EQ"}}
                **Non-Time-Based Queries:**

                * If there are no explicit time references in the query, return an filter based on the following keyword logic.
                * If query contains the word major return filter as {{"key":"is_major", "value": "1", "operator": ""}}.
                * If query contains the word home run` return filter as {{"key":"homerun", "value": "1", "operator": ""}}.
                * If query contains the word `out` return filter as  {{"key":"out", "value": "1", "operator": ""}}.
                * If there are no time or event type related keyword match in the query return an empty filter `{{}}`.

                **Filter Output:**
                - Output should be a JSON dictionary, only containing the time filter or one of the event type filter or an empty dictionary {{}}.
                - The `value` for the time is always numerical and always represents a number in seconds.
                - The value for event type is always a string and can be 0 or 1.

                This is the user query:{query}
                This is the current time:{current_time}
                """),
            expected_output=dedent("""
            **Output:**
            A JSON object containing the `filter`.

                **Filter Output:**

                - A filter is a JSON dictionary with keys `key`, `value`, and `operator`.
                - Time filters use the key `time`. The value is numerical and represents a time in seconds.
                - Non-time filters use key as a category of events such as `is_major`, `homerun` , `out`. The value for the non-time filters is always a string and can be 0 or 1
                - If there is no time or event type related query output filter as `{{}}`.

                Examples:
                    User Query: "What happened 30 seconds back", Current time: "50 seconds", Output: {{"key":"time", "value": 20, "operator": "LT"}}
                    User Query: "What happened exactly 40 seconds back", Current time: "50 seconds", Output: {{"key":"time", "value": 10, "operator": "EQ"}}
                    User Query: "What happened from 30 seconds back till now", Current time: "50 seconds", Output: {{"key":"time", "value": 20, "operator": "GT"}}
                    User Query: "since last 20 sec", Current time: "50 seconds", Output: {{"key":"time", "value": 30, "operator": "GT"}}
                    User Query: "What happened", Current time: "50 seconds", Output: {{}}
                    User Query: "tell me when did the last bunting happen", Current time: "50 seconds", Output: {{"key":"time", "value": 50, "operator": "LT"}}
                    User Query: "Show me the latest homerun", Current time: "50 seconds", Output: {{"key":"time", "value": 50, "operator": "LT"}}
                    User Query: "show me events tagged with 'news'", Current time: "50 seconds", Output: {{}}
                    User Query: "show me events tagged with 'news' or 'sport'", Current time: "50 seconds", Output: {{}}
                    User Query: "Show me major events related to bunting or strike or homerun", Current time: "50 seconds", Output: {{"key":"is_major", "value": "1", "operator": ""}}
                    User Query: "Show me all the homerun", Current time: "50 seconds", Output: {{"key":"homerun", "value": "1", "operator": ""}}
                    User Query: "Show me all the out", Current time: "50 seconds", Output: {{"key":"out", "value": "1", "operator": ""}}

            """),
            agent=self.query_optimizer_agent,
            output_json=VectorSearchFilter
        )

        self.query_modification_task = Task(
            description=dedent("""
                **Task:** Modify Queries for Vector Search

                You are an expert in processing user queries and modifying them for vector database searches, with a focus on baseball-related information.
                You will receive:
                1. A **user query** describing the information they seek (e.g., "What happened 30 seconds ago?", "When did bunting occur?", "Show me the latest homerun").

                Your goal is to:
                    1. Modify the query to '*' for all time-related queries, unless it contains a baseball term with time. In that case just extract the baseball term.
                    2. Modify non-time-based queries which are not explicitly baseball terms to more specific baseball-related queries, using terms like "homerun," "strikeout," "bunting," etc. Retain the original query if it contains multiple baseball terms.

                **Query Modification Logic:**

                **Time-Based Queries:**

                When the query contains explicit references to time (e.g., "30 seconds ago," "last 5 minutes"), change the search query to '*':
                - Unless the time based query has baseball terms included, then extract only the baseball terms from the query
                **Non-Time-Based Queries:**

                    * If there are no explicit time references in the query, and the query is not related to baseball terms, convert the query to a more user friendly, specific baseball-related query. Consider terms such as "homerun", "strikeout", "bunt", "stolen base", "double play", "walk", etc. Use the most appropriate terms to reflect the user's intent. If the query cannot be converted to a specific baseball term, convert it to " ".
                    * If multiple baseball-related terms are already present in the query, retain the original query.

                **Hybrid Time and Baseball Queries:**

                When the query is in the format "When did [baseball term] occur?", or "Show me the latest [baseball term]":
                    - Change the search query to the 'baseball term' itself (e.g., "homerun", "bunting", etc).
                    - If time related and the query has a baseball term, retain the baseball term along with extra info in query such as a players name.

                **Modified Query Output:**

                    - For all time-related queries, the modified query should be '*' , unless the query contains a baseball term, in that case extract the baseball term.
                    - For non-time related queries, the query should be modified to specific baseball terms where possible. If the query is not related to baseball or does not contain a baseball term then use " ". If the user query already contains multiple baseball terms, then return the original user query.

                This is the user query:{query}


                """),
            expected_output=dedent("""
                **Output:**
                A JSON object containing the `modified_query`.

                **Modified Query Output:**

                - For all time related queries the modified query should be '*' unless the query contains a baseball term, in that case extract the baseball term.
                - For non-time related queries:
                    - If the query is not related to baseball terms, convert it to specific baseball events such as 'homerun', 'strikeout', 'bunt', 'stolen base', 'double play', 'walk' etc.
                    - If the query cannot be converted to a specific baseball term, use "".
                    - If the user query already contains multiple baseball terms, then return the original user query.

                Examples:
                    User Query: "What happened 30 seconds back", Output: {{"modified_query":"*"}}
                    User Query: "What happened exactly 40 seconds back", Output: {{"modified_query":"*"}}
                    User Query: "What happened from 30 seconds back till now", Output: {{"modified_query":"*"}}
                    User Query: "What happened", Output: {{"modified_query":"baseball major events"}}
                    User Query: "tell me when did the last bunting happen", Output: {{"modified_query":"bunting"}}
                    User Query: "Show me the latest homerun", Output: {{"modified_query":"homerun"}}
                    User Query: "Show me major events related to bunting or strike or homerun", Output: {{"modified_query":"Show me major events related to bunting or strike or homerun"}}
                    User Query: "when was the last walk event?", Output: {{"modified_query":"walk"}}
                    User Query: "what about the latest stolen base?", Output: {{"modified_query":"stolen base"}}
                    User Query: "any double plays recently", Output: {{"modified_query":"double play"}}
                    User Query: "when did Shohei Ohtani hit a homerun?", Output: {{"modified_query":"Shohei Ohtani homerun"}}
                    User Query: "provide be the bunts that happended 20s back", Output: {{"modified_query":"bunt"}}
                    User Query: "provide me homerrun that happened x time back", Output: {{"modified_query":"homerun"}}
                    User Query: "provide me all major events happen", Output: {{"modified_query":""}}
            """),
            agent=self.query_optimizer_agent,
            output_json=ModifiedQuery,
        )

        self.vector_search_task = Task(
            description=dedent("""
                **Task:** Retrieve, Filter, and Sort Chunks from the Vector Database Based on "Latest" Queries

                You are an expert at using a vector database to retrieve relevant information.
                You will receive:
                1. A ** vector_query ** {vector_query} describing the query that needs to be passed to search vector database.
                2. A **filter ** {filter} which will be used initially to narrow down the results .

                Your goal is to:
                1. Use the provided 'search_vector_db' tool to query the vector database. **Use the filter provided {filter} ** along with the vector_query provided {vector_query} .

                2. **Initial Fetch and Examine**: Fetch the chunks from the vector database using the query and filter expression and examine the metadata (specifically timestamp metadata) to further determine which chunks are relevant to the query {query}.

                3. **Time-Based Post-Filtering**
                - After retrieval, you must use the timestamps metadata associated with each chunk to filter the list of chunks further and include only chunks that are relevant to the {query} also take into consideration the current time {current_time}.

                4. **"Latest" Handling**:
                    - If the user query includes a requirement for "latest" (e.g. "the latest event", "based on latest"), you must use the timestamps metadata to filter or sort accordingly.
                    - If the query asks for the *latest* event, filter to return only the chunk with the most recent timestamp.
                    - If the query asks for events *based on latest*, sort the chunks in descending order by timestamp.

                5. **Return Results**: Return the list of chunks after they have been filtered and sorted.


                **Important Considerations:**
                - Pay close attention to the **filter expression**; it is vital for accurate initial retrieval.
                - After retrieval, you must analyze the metadata (specifically timestamps) to accurately filter to the correct time frame and to process 'latest' type queries.
                - The need for further filtering beyond timestamps and the sorting criteria can vary depending on the query.
                - The output should be a list of chunks that satisfies the user query.
                - The chunks should be sorted by relevancy and then by recency or by recency if user asks for events based on latest.
                - None of the retrieved chunks should have time metadata greater than {current_time}
            """),
            expected_output=dedent("""
                **Output:** A list of chunks that have been filtered according to the filter expression and the time-based constraints of the user query, further filtered based on query or context, and then sorted by relevance to the query and then recency or by recency if user asks for events based on latest. The output should be a list of raw chunks as found in the database (no summarization)
            """),
            agent=self.retrieval_agent,
            tools=[VectorDBSearchTool()],
        )

        self.mlb_information_gathering_task = Task(
            description=dedent("""
                You are provided with a user query: {query}.
                Your goal is to use the 'search_tool' to find relevant URLs and then use the 'scrape_web' tool to gather information which can help answer the user query {query}. As soon as you know the answer just return it and dont go for further use of search and scrape web tool.
                Your primary focus is answering the user query based on all the information extracted.
                Return the answer to the user query {query} along with the required citations from where you have answered the user query.
                """),
            expected_output=dedent("""
                The output should answer the user query {query} and should also include citation. It should be a json with answer and citations.
                """),
            agent=self.mlb_information_agent,
            output_json=SearchOutput,
        )

        self.answer_generation_task = Task(
            description=dedent("""
                You are provided with a user query: {query} and a list of relevant text chunks.
                The current time is: {current_time}

                Analyze the text chunks provided and follow the following instructions.
                Your goal is to answer the user's query using only the information provided in the text chunks.
                If the chunks do not contain the information to answer the query, respond that the answer cannot be determined from the provided information.
                Be concise and direct in your response. Do not mention anything about the citations or file name in the answer you can only add the time of req.

                Please return the output in a JSON format with keys "answer", "query", and "citations" where "citations" is an array of filenames provided in the meta data of the chunk.
                Whenever there is anything as a number followed by a t just replace t with seconds for example 450t is 450s.
                """),
            expected_output=dedent("""
                A JSON formatted string containing the answer to the user's query {query} based on the provided chunks. The output will contain keys: "answer", "query" and "citations", where citations is an array of filenames. If the information is not available, then respond with an appropriate message in the "answer" key. Only use those information from the chunks which is required to answer the {query} dont add additional unwanted information from the chunk. See to it that the answer as logical flow and use the time metadata to make the answer better.
                """),
            agent=self.retrieval_agent,
            context=[self.vector_search_task],
            output_json=HistoricalOutput,
        )

    def run(self, query, video, current_time):
        """
        Executes the baseball analysis workflow based on the user query type.

        Args:
            query (str): The user's query string.
            video (str): The path to the video file.
            current_time (str): The current time as a reference.

        Returns:
            str: The final result of the analysis, formatted as a JSON string.
        """
        print("\n--- Starting Baseball Analysis Workflow ---")
        print(f"  User Query: {query}")
        print(f"  Current Time: {current_time}")

        try:
            # Initial setup with combined query agent
            data_dict = {"query": query}
            crew = Crew(
                agents=[self.query_optimization_agent],
                tasks=[self.query_analysis_task],
                verbose=True,
                process=Process.sequential,
            )
            query_analysis_result = crew.kickoff(inputs=data_dict)

            print(f"  Query Analysis Result: {query_analysis_result}")

            # Check the type of query and proceed accordingly
            if query_analysis_result['type'] == "realtime":
                try:
                    print("\n  Processing as a Real-Time Query...")
                    # Real-time video analysis
                    data_dict = {"question": query_analysis_result['optimized_query'], "video": video}
                    crew.tasks = [self.realtime_video_analysis_task]
                    crew.agents = [self.realtime_analysis_agent]
                    realtime_result = crew.kickoff(inputs=data_dict).json_dict
                    final_result = {"result": realtime_result, "type": "realtime"}
                    print(f"  Real-Time Analysis Result: {final_result}")
                    return json.dumps(final_result)
                except Exception as e:
                    print(f"  Error during real-time processing: {e}")
                    return str({"error": f"Error during real-time processing: {e}"})

            elif query_analysis_result['type'] == "historical":
                try:
                    print("\n  Processing as a Historical Query...")
                    # Historical data retrieval and RAG
                    data_dict = {"query": query_analysis_result['optimized_query'], "current_time": current_time}
                    crew.tasks = [self.query_modification_task, self.vector_search_filter_task]
                    crew.agents = [self.query_optimizer_agent]
                    filter_and_modified_query_results = crew.kickoff(inputs=data_dict)

                    modified_query = self.query_modification_task.output.json_dict["modified_query"]
                    filter_key = self.vector_search_filter_task.output.json_dict["key"]
                    filter_value = self.vector_search_filter_task.output.json_dict["value"]
                    filter_operator = self.vector_search_filter_task.output.json_dict["operator"]

                    data_dict = {"vector_query": modified_query, "filter": str({"key": filter_key, "value": filter_value, "operator": filter_operator}),
                                 "query": query_analysis_result['optimized_query'], "current_time": current_time}
                    crew.tasks = [self.vector_search_task, self.answer_generation_task]
                    crew.agents = [self.retrieval_agent]
                    historical_result = crew.kickoff(inputs=data_dict).json_dict
                    final_result = {"result": historical_result, "type": "historical"}
                    print(f"  Historical Analysis Result: {final_result}")
                    return json.dumps(final_result)
                except Exception as e:
                    print(f"  Error during historical processing: {e}")
                    return str({"error": f"Error during historical processing: {e}"})

            else:
                try:
                    print("\n  Processing as a Search Query...")
                    # General information gathering
                    data_dict = {"query": query_analysis_result['optimized_query']}
                    crew.tasks = [self.mlb_information_gathering_task]
                    crew.agents = [self.mlb_information_agent]
                    search_result = crew.kickoff(inputs=data_dict).json_dict
                    final_result = {"result": search_result, "type": "search"}
                    print(f"  Search Query Result: {final_result}")
                    return json.dumps(final_result)
                except Exception as e:
                    print(f"  Error during search processing: {e}")
                    return str({"error": f"Error during search processing: {e}"})

        except Exception as e:
            print(f"  An unexpected error occurred: {e}")
            return str({"error": f"An unexpected error occurred: {e}"})
