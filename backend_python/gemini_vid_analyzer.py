import os
import re
import time
from typing import List
from google import genai
from google.genai import types
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import tenacity
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
DETAILED_GAME_ANALYSIS_PROMPT = """Analyze the provided video of a baseball game.

**Deliverables:**

Return a JSON object with the following keys:

1.  **"play_by_play"**: A string providing a detailed and engaging explanation of the play, as if giving live sports commentary. Focus on key actions by players (batter, pitcher, runners, fielders), including pitch type (if discernible), swing mechanics, ball trajectory, and fielder movements. Include player names if identifiable. Utilize audio cues (e.g., bat crack, crowd reaction, umpire calls) to enrich the description and add to the excitement. The play-by-play should be descriptive and capture the flow of the play as it unfolds, providing context and highlighting any noteworthy aspects. If no play occurs, provide a brief summary of the scene, like "The pitcher is taking their warm-up tosses on the mound" or "We're in a timeout, the dugout is engaged in conversation".
    
2.  **"major_events"**: A string containing a list of all major events that occur during the video, with their start and end timestamps in the format "start-end: Event description" (rounded to the nearest second). Major events include:
    *   Home Run
    *   Single
    *   Double
    *   Triple
    *   Stolen Base
    *   Caught Stealing
    *   Walk
    *   Hit By Pitch
    *   Strikeout (swinging or looking)
    *   Wild Pitch (advances runner(s))
    *   Passed Ball (advances runner(s))
    *   Balk
    *   Double Play
    *   Triple Play
    *   Error (significant impact on play outcome)
    *   Fielder's Choice
    *   Sacrifice Bunt
    *   Sacrifice Fly
    *   Infield Fly
    *   Ground-Rule Double
    *   Interference
    *   Uncaught Third Strike
    *   Force out
    *   Tag out
    *    Pick Off
    along with these include other major events that you think are important pertaining to baseball game above are just examples dont restrict to these only.

    If no major events occur, return an empty string. Timestamps are relative to the start of the video segment. Separate multiple major events with a semicolon (`;`).

3.  **"is_major"**:  A string, either "0" or "1".  Return "1" if any major event occurs in the video segment, otherwise return "0".
4.  **"homerun"**: A string, either "0" or "1". Return "1" if a home run occurs during the video segment, otherwise return "0".
5. **"out"**: A string, either "0" or "1". Return "1" if any batter is out during the video segment (via strikeout, force out, tag out, fly out, etc.) otherwise return "0".
6. **"strategies"**: A string containing a list of baseball strategies observed in the video segment, separated by a semicolon (;). These may include (but are not limited to):
    *   Stealing a base
    *   Hit and Run
    *   Bunting (Sacrifice, Bunt for Hit)
    *   Intentional Walk
    *   Pitching around a batter (if clearly visible)
    *   Defensive shift
    *   Pick off attempt
   *   squeeze play

*   If the video contains no play, return an empty string for "major_events" and "0" for "is_major." "play_by_play" should still give a short description of what is happening if there is no play.

**Output Format:**
Return a JSON object with the following structure:

```json
{
  "play_by_play": "...",
  "major_events": "...",
  "is_major": "...",
  "homerun": "...",
  "out": "...",
  "strategies": "..."
}
Example Output:
For a play with a single, followed by a successful steal:
{
  "play_by_play": "The pitcher winds up and delivers a fastball, low and inside. Smith makes contact, sending a grounder towards the shortstop. The shortstop fields it cleanly, but Smith is just too quick, beating the throw to first for a single.  Now Smith takes a good lead off of first base, the pitcher goes into his windup and Smith takes off! He slides into second base, and the umpire signals safe! Steal of second!",
  "major_events": "15-17: Stolen base; 5-7: Single",
  "is_major": "1",
  "homerun": "0",
  "out": "0",
    "strategies": "Stealing a base"
}
For a play with a double play:
{
  "play_by_play": "The pitcher comes set and throws a curveball right over the heart of the plate. Jones swings, hitting a sharp grounder right to the shortstop. The shortstop fields it quickly and fires to second base for the force out! The second baseman makes the turn and throws to first, getting the runner by a hair for an incredible double play!",
  "major_events": "22-25: Double play",
  "is_major": "1",
  "homerun": "0",
  "out": "1",
  "strategies": ""
}
For a play with a home run:
{
  "play_by_play": "The pitcher fires a fastball, high and inside, and oh wow! Jones unleashes a mighty swing and connects! The ball is sailing, a towering shot! It's outta here! That's a home run! The crowd is going wild!",
  "major_events": "2-5: Home Run",
   "is_major": "1",
  "homerun": "1",
  "out":"0",
  "strategies": ""
}
For a play with a strike out:
{
  "play_by_play": "The pitcher is on the mound and starts with a fastball for strike one. Next, a looping curveball for strike two. The crowd is getting excited. Here comes another curve, and Davis swings! Strike three! He's out!",
  "major_events": "0-4: Strikeout",
  "is_major": "1",
  "homerun": "0",
    "out": "1",
    "strategies": ""
}
For a video segment with no major events, but still has play:
{
 "play_by_play": "Williams steps up to the rubber and throws a fastball, Anderson steps out of the box to adjust his gloves. Williams gets the sign from his catcher and throws a curveball, Anderson back in the batter's box.",
 "major_events": "",
 "is_major": "0",
 "homerun":"0",
  "out": "0",
  "strategies": ""
}
For a video segment with no relevant player action:
{
 "play_by_play": "The pitcher is standing on the mound, adjusting his cap. Nothing happening at the moment, the game is in a bit of a lull.",
 "major_events": "",
 "is_major": "0",
 "homerun": "0",
  "out": "0",
   "strategies": ""
}
For a play with a sacrifice bunt:
{
  "play_by_play": "The batter squares up to bunt, and drops it right in front of the plate. He runs towards first. The pitcher fields the ball and throws to first and the batter is easily out. The runner on first advances to second. A textbook sacrifice bunt.",
  "major_events": "2-4: Sacrifice Bunt",
  "is_major": "1",
  "homerun": "0",
  "out": "1",
  "strategies": "Bunting (Sacrifice)"
}
"""
SYSTEM_PROMPT = "When given a video and a query, call the relevant function only once with the appropriate timecodes and text for the video"


class VideoAnalyzer:
    """
    This class provides methods for analyzing baseball videos using the Google Gemini API.
    It supports video uploading, analysis with specific prompts, and saving the analysis results to files.
    It also supports processing multiple video segments in parallel using a thread pool executor.
    """
    def __init__(self, api_key, model_id):
        """
        Initializes the VideoAnalyzer with the API key, model ID, system prompt, and detailed analysis prompt.

        Args:
            api_key (str): The API key for the Google Gemini API.
            model_id (str): The ID of the Gemini model to use.
            system_prompt (str): The system prompt to guide the model's behavior.
            detailed_analysis_prompt (str): The prompt used to perform detailed analysis on the video content.
        """
        self.client = genai.Client(api_key=api_key)  # Initialize the Gemini API client.
        self.model_id = model_id  # Store the model ID.
        self.system_prompt = SYSTEM_PROMPT
        self.detailed_analysis_prompt = DETAILED_GAME_ANALYSIS_PROMPT


    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10), retry=retry_if_exception_type(ValueError))
    def analyze_baseball_video(self, video_path, user_prompt):
        """
        Analyzes a single baseball video using the Gemini API.
        Retries the analysis up to 3 times with a 10-second delay if a ValueError occurs.

        Args:
            video_path (str): The path to the video file.
            user_prompt (str): The user prompt to guide the analysis.

        Returns:
            str: The text response from the Gemini API after analyzing the video.

        Raises:
            ValueError: If the video processing fails after multiple retries.
        """
        file_upload = self.client.files.upload(path=video_path)  # Upload the video file to the API.
        while file_upload.state == "PROCESSING":  # Poll the upload status until it's complete.
            print('Waiting for video to be processed.')
            time.sleep(10)  # Wait for 10 seconds before checking again.
            file_upload = self.client.files.get(name=file_upload.name)  # Get the updated file status.
        if file_upload.state == "FAILED":  # Raise an error if the video processing failed.
            raise ValueError(f"Video processing failed: {file_upload.state}")
        print(f'Video processing complete: ' + file_upload.uri)
        prompt = user_prompt  # Use the user prompt for the analysis.
        response = self.client.models.generate_content(  # Generate content using the Gemini API.
            model=self.model_id,  # Specify the model to use.
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_uri(file_uri=file_upload.uri, mime_type=file_upload.mime_type)]  # Add the video file as a part of the content.
                ),
                prompt,  # Add the user prompt as part of the content.
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,  # Provide a system instruction.
                temperature=0.0,  # Set the temperature to 0 for more deterministic output.
            ),
        )
        return response.text  # Return the text response from the API.

    def analyze_and_save(self, video_path, prompt, output_dir, segment_name):
        """
        Analyzes a single video and saves the analysis result to a text file.
        """
        try:
            analysis = self.analyze_baseball_video(video_path, prompt)  # Analyze the video using the specified prompt.
            response_file = os.path.join(output_dir, f"{segment_name}.txt")  # Create the output file path.
            with open(response_file, "w") as f:  # Open the file in write mode.
                f.write(analysis)  # Write the analysis result to the file.
            print(f"Successfully processed and saved: {video_path}")  # Print message on successful analysis
            return True # Indicate success
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            return False # Indicate failure

    @staticmethod
    def extract_segment_number(filename):
        """
        Extracts the segment number from the filename using regex.

        Args:
            filename (str): The filename of the video segment.

        Returns:
            int: The segment number if found, otherwise float('inf').
        """
        match = re.search(r'segment_(\d+)\.mp4', filename)  # Search for the pattern "segment_(\d+).mp4" in the filename.
        if match:
            return int(match.group(1))  # Return the captured segment number as an integer.
        return float('inf')  # Put files that don't match at the end, ensures files without segment number appear at the end when sorting

    def process_segments(self, video_dir, output_dir, max_workers=4, max_retries=3):
        """
        Processes multiple video segments in parallel using a thread pool executor.

        Args:
            video_dir (str): The directory containing the video segments.
            output_dir (str): The directory to save the analysis results.
            max_workers (int): The maximum number of worker threads to use.
            max_retries (int): The maximum number of times to retry failed files.
        """
        if not os.path.exists(output_dir):  # Check if output directory exists.
            os.makedirs(output_dir)  # Create the output directory if it doesn't exist.
        event_dir = os.path.join(output_dir, "event")
        if not os.path.exists(event_dir): # specific event directory, adjust name if required.
            os.makedirs(event_dir) # Create an event directory within the output directory to save segment analysis results.

        video_files = sorted([entry.path for entry in os.scandir(video_dir) if entry.is_file() and entry.name.endswith(".mp4")], key=self.extract_segment_number) # Grab all .mp4 files and then sort the files based on its filename
        # List of files in `video_dir`, keeping only the file paths, ensures the filename contains ".mp4" and sorting the files based on segment number extracted from the filename

        failed_files = video_files.copy() #Initially assume all have failed

        for retry_attempt in range(max_retries + 1):
          if not failed_files:
            print("All files processed successfully!")
            break # Break the loop once there are no more failed files.

          print(f"\n--- Retry Attempt {retry_attempt}/{max_retries} ---")

          with ThreadPoolExecutor(max_workers=max_workers) as executor:  # Create a thread pool executor with the specified number of worker threads.
              with tqdm(total=len(failed_files), desc="Processing video segments") as pbar:  # Initialize a progress bar.
                  futures = {}  # Dictionary to store futures and their corresponding video paths
                  for video_path in failed_files:  # Iterate over each video file that previously failed.
                      file_name = os.path.basename(video_path)  # Get the filename from the video path.
                      segment_name = os.path.splitext(file_name)[0]  # Remove the extension from the filename to get the segment name.
                      future = executor.submit(  # Submit the analysis task to the thread pool executor.
                          self.analyze_and_save,  # Call the analysis function.
                          video_path,  # Pass the video path.
                          self.detailed_analysis_prompt,  # Pass the detailed analysis prompt.
                          event_dir,  # Pass the output directory to event directory.
                          segment_name,  # Pass the segment name.
                      )
                      futures[video_path] = future  # Store the future with the video path as the key

                  successful_files = [] # Keep track of the files processed successfully in this retry attempt.
                  for video_path, future in tqdm(futures.items(), desc="Collecting Results"):  # Iterate through the futures dictionary
                      try:
                          if future.result(): # Get result, is True when successful
                              successful_files.append(video_path) #Store the file path if it was successful
                      except Exception as e:
                          print(f"Task failed for {video_path} with exception: {e}") # Print exception, though the retry would catch it anyway.
                      pbar.update(1)

          # Update the list of failed files by removing successfully processed files
          failed_files = [f for f in failed_files if f not in successful_files]

        if failed_files:
            print("\nFiles that FAILED after all retries:")
            for file_path in failed_files:
                print(file_path)
        else:
            print("\nAll files processed SUCCESSFULLY after retries!")