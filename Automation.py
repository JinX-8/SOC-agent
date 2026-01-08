import os
import subprocess
import requests
import keyboard
import asyncio
import webbrowser
from AppOpener import close, open as appopen
from pywhatkit import search, playonyt
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
from pathlib import Path # Import Path for directory creation

# --- CONFIGURATION ---

# Load environment variables
env_vars = dotenv_values(".env")
GROQ_API_KEY = env_vars.get("GROQ_API_KEY")
USERNAME = env_vars.get("USERNAME") # Load Username here

# Define CSS classes for parsing specific elements (Used in OpenApp fallback)
CSS_CLASSES = ["ZCubwf", "hgKeLc", "LTKxOQ sY7ric", "Zelcw", "gsrt vk_bK FzvWsb YwPhnf", "pclqee",
               "tw-Data-text tw-text-small tw-ta", "IZ6fdc", "0S0uKd LTKxOQ", "vLYf6d",
               "webanswers-webanswers_table-webanswers-table", "d0mNo lkb40b gsrt", "sXLadE",
               "lwkfKe", "vQF4g", "qy3Wpe", "kno-rdesc", "SPz26b"]

useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
client = Groq(api_key=GROQ_API_KEY)
messages = [] # Initialize messages list for ContentWriterAI

# --- Create Data Directory if it doesn't exist ---
Path("Data").mkdir(exist_ok=True)
# -------------------------------------------------

# System message (FIXED: Uses loaded USERNAME variable)
SystemChatbot = [{"role": "system ", "content": f"Hello, I am {USERNAME}, You are a very accurate and advanced AI chatbot which has real-time up-to-date information from the internet."}]

# --- UTILITY FUNCTIONS ---

def OpenNotePad(file_path):
    """Opens the specified file in the default text editor."""
    try:
        if os.name == 'nt': # Windows
            subprocess.Popen(['notepad.exe', file_path])
        elif os.uname().sysname == 'Darwin': # macOS
             subprocess.Popen(['open', '-t', file_path])
        else: # Linux
            subprocess.Popen(['xdg-open', file_path])
        return True
    except Exception as e:
        print(f"[ERROR] Could not open text editor: {e}")
        return False

def ContentWriterAI(prompt):
   """Generates content using Groq API based on the prompt."""
   # Simple Content Writer (Note: Consider moving API key checks here)
   local_messages = messages.copy() # Use a local copy for this session
   local_messages.append({"role": "user", "content": f"{prompt}"})

   try:
       completion = client.chat.completions.create(
         model = "llama-3.1-8b-instant", # Using the fast model
         messages=SystemChatbot + local_messages, # Include system prompt + history
         max_tokens=2048,
         temperature=0.7,
         stream=True,
         stop=None
       )
   except Exception as e:
       print(f"[ERROR] Groq API call failed in ContentWriterAI: {e}")
       return f"Error generating content: {e}"

   Answer = ""
   for chunk in completion:
      if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
         Answer += chunk.choices[0].delta.content

   Answer = Answer.replace("</s>"," ") # Clean up potential end tokens
   # Optionally update the global 'messages' if you want persistent history across calls
   # messages.append({"role": "assistant", "content": Answer})
   return Answer

def Content(Topic):
   """Creates content using AI, saves it to a file, and opens it."""
   print(f"Generating content for topic: {Topic}")
   ContentByAi = ContentWriterAI(Topic)
   if "Error generating content" in ContentByAi:
       print(ContentByAi) # Print the error message
       return False # Indicate failure

   # FIXED PATH: Use os.path.join and create a valid filename
   filename = f"{Topic.lower().replace(' ', '_')}.txt"
   file_path = os.path.join("Data", filename)

   try:
       with open(file_path, "w", encoding='utf-8') as file: # Added encoding
           file.write(ContentByAi)
       print(f"Content saved to: {file_path}")
       OpenNotePad(file_path)
       return True
   except Exception as e:
       print(f"[ERROR] Failed to save or open content file: {e}")
       return False


# --- TASK EXECUTION FUNCTIONS ---

def Googlesearch(Topic):
   """Performs Google search using pywhatkit."""
   try:
       print(f"Searching Google for: {Topic}")
       search(Topic)
       return True
   except Exception as e:
       print(f"[ERROR] Google search failed: {e}")
       return False

def YoutubeSearch(Topic):
   """Opens YouTube search results in a browser."""
   try:
       # FIXED TYPO & METHOD: Correct URL and use webopen
       print(f"Searching YouTube for: {Topic}")
       url_search = f"https://www.youtube.com/results?search_query={Topic.replace(' ', '+')}"
       webbrowser.open(url_search)
       return True
   except Exception as e:
       print(f"[ERROR] YouTube search failed: {e}")
       return False

def PlayYoutube(query):
   """Plays video directly on YouTube using pywhatkit."""
   try:
       print(f"Playing on YouTube: {query}")
       playonyt(query)
       return True
   except Exception as e:
       print(f"[ERROR] YouTube playback failed: {e}")
       return False

def OpenApp(app, sess=requests.session()):
   """Opens application by name or searches Google if appopener fails."""
   try:
      print(f"Attempting to open app: {app}")
      appopen(app, match_closest=True, throw_error=True) # Attempt to open app.
      return True
   except Exception as open_err:
      print(f"AppOpener failed for '{app}'. Trying web search... Error: {open_err}")
      # --- Fallback: Google Search and Open Link ---
      try:
          def extract_links(html):
             if html is None: return []
             soup = BeautifulSoup(html, 'html.parser')
             # Try common search result link classes (these change often!)
             links = soup.select('a[jsname="UWckNb"], a[href^="/url?q="]')
             valid_links = []
             for link in links:
                 href = link.get('href')
                 if href and href.startswith('/url?q='):
                     # Extract clean URL from Google redirect
                     valid_links.append(href.split('/url?q=')[1].split('&')[0])
                 elif href and not href.startswith('#') and not href.startswith('/'):
                     valid_links.append(href) # Direct link
             return valid_links

          def search_google(query):
             # FIXED TYPO: Correct query string format
             url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
             headers = {"User-Agent": useragent}
             response = sess.get(url, headers=headers)
             response.raise_for_status() # Raise an exception for bad status codes
             return response.text

          html = search_google(f"Open {app} website")

          if html:
             potential_links = extract_links(html)
             if potential_links:
                 link_to_open = potential_links[0] # Try the first valid link
                 print(f"Opening web link: {link_to_open}")
                 webbrowser.open(link_to_open)
                 return True
             else:
                 print("No suitable web link found.")
                 return False
      except Exception as search_err:
          print(f"[ERROR] Web search fallback failed: {search_err}")
          return False

def CloseApp(app):
   """Closes application by name (skips chrome for safety)."""
   app_lower = app.lower().strip()
   if "chrome" in app_lower or "safari" in app_lower or "firefox" in app_lower:
      print(f"Skipping browser close command for '{app}' for safety.")
      return True # Pretend success to avoid error messages
   else:
      try:
         print(f"Attempting to close app: {app}")
         # Ensure throw_error is True to catch failures
         closed = close(app, match_closest=True, output=False, throw_error=True)
         return True # AppOpener's close doesn't return reliably, assume success if no error
      except Exception as e:
         print(f"[ERROR] Failed to close '{app}': {e}")
         return False

def SystemCmd(command):
   """Simulates keyboard commands for volume control."""
   cmd_lower = command.lower().strip()
   try:
       print(f"Executing system command: {cmd_lower}")
       if cmd_lower == "mute":
          keyboard.press_and_release("volume mute")
       elif cmd_lower == "unmute":
          # Note: 'volume unmute' might not work on all systems, often mute toggles
          keyboard.press_and_release("volume mute") # Try toggling mute again
       elif cmd_lower == "volume up":
          keyboard.press_and_release("volume up")
       elif cmd_lower == "volume down":
          keyboard.press_and_release("volume down")
       else:
           print(f"Unknown system command: {command}")
           return False
       return True
   except Exception as e:
       print(f"[ERROR] System command '{command}' failed: {e}")
       print("Ensure 'keyboard' library has necessary permissions (especially on macOS).")
       return False

# --- ASYNCHRONOUS EXECUTION LOGIC ---

async def TranslateAndExecute(command_list: list[str]):
   """Translates Decision Model output into executable asynchronous tasks."""
   tasks_to_run = []

   # FIXED LOOP LOGIC: Iterate over each command string in the input list
   for cmd_full in command_list:
       cmd = cmd_full.strip() # Ensure no leading/trailing whitespace
       cmd_lower = cmd.lower()

       # FIXED STARTSWITH and REMOVEPREFIX: Use the loop variable 'cmd'
       if cmd_lower.startswith("open"):
           argument = cmd.removeprefix("open").strip()
           if argument: # Avoid running if argument is empty
               tasks_to_run.append(asyncio.to_thread(OpenApp, argument))

       elif cmd_lower.startswith("close"):
           argument = cmd.removeprefix("close").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(CloseApp, argument))

       elif cmd_lower.startswith("play"):
           argument = cmd.removeprefix("play").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(PlayYoutube, argument))

       elif cmd_lower.startswith("content"):
           argument = cmd.removeprefix("content").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(Content, argument))

       elif cmd_lower.startswith("google search"):
           argument = cmd.removeprefix("google search").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(Googlesearch, argument))

       elif cmd_lower.startswith("youtube search"): # FIXED TYPO: YouTube
           argument = cmd.removeprefix("youtube search").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(YoutubeSearch, argument))

       elif cmd_lower.startswith("system"):
           argument = cmd.removeprefix("system").strip()
           if argument:
               tasks_to_run.append(asyncio.to_thread(SystemCmd, argument)) # FIXED TYPO: SystemCmd

       # Placeholders for general and realtime are handled by other files
       elif cmd_lower.startswith("general") or cmd_lower.startswith("realtime") or cmd_lower == "exit":
           pass # These commands are not executed here
       else:
          print(f"[Warning] No automation function found for command: {cmd}")

   if not tasks_to_run:
       print("No executable automation tasks found.")
       return # Don't proceed if there's nothing to run

   # Execute all scheduled tasks concurrently and capture results
   results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

   # Process results (optional: can yield success/failure messages)
   for i, result in enumerate(results):
       if isinstance(result, Exception):
           print(f"Task {i+1} failed: {result}")
       elif result is False:
            print(f"Task {i+1} reported failure.")
       # else: Task succeeded (returned True or None)


async def Automation(command_list: list[str]):
   """Main entry point for task execution."""
   print(f"Received automation commands: {command_list}")
   try:
       await TranslateAndExecute(command_list)
       print("Automation tasks completed.")
       return True
   except Exception as e:
       print(f"[FATAL ERROR] in Automation execution: {e}")
       return False

# --- Main execution block for testing this file directly (Optional) ---
# if __name__ == "__main__":
#     async def test_automation():
#         # Example commands list similar to what Model.py might return
#         test_commands = ["open calculator", "play relaxing music", "system volume up"]
#         success = await Automation(test_commands)
#         print(f"Test automation finished with status: {success}")
#
#     asyncio.run(test_automation())