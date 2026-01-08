import os
from pathlib import Path 
import datetime 
from json import load, dump
import groq
from dotenv import dotenv_values 

# --- Directory Setup (Fixes [Errno 2]) ---
# Ensure the 'Data' folder exists before we try to read/write files.
Path("Data").mkdir(exist_ok=True)
# ----------------------------------------

# --- Configuration ---
# Load environment variables from .env file
env_vars = dotenv_values(".env")

# Retrieve specific environment variables 
Username = env_vars.get("USERNAME")
AssistantName = env_vars.get("ASSISTANT_NAME")
GROQ_API_KEY = env_vars.get("GROQ_API_KEY")

# INITIALIZE GROQ CLIENT
client = groq.Groq(api_key=GROQ_API_KEY)

# Define the system message that provides context to the AI chatbot 
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {AssistantName} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

SystemChatbot = [{"role": "system", "content": System}]


# --- Helper Functions ---

# Function to get real-time date and time 
def get_current_datetime():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A") 
    date = current_date_time.strftime("%d") 
    month = current_date_time.strftime("%B") 
    year = current_date_time.strftime("%Y") 
    hour = current_date_time.strftime("%I") 
    minute = current_date_time.strftime("%M") 
    second = current_date_time.strftime("%S") 

    # Format the information into a string 
    data = f"Please use this real-time information if needed,\n"
    data += f"Day : {day}, Date : {date} {month} {year}, Time : {hour}:{minute}:{second}\n"
    return data

# Function to modify the chatbot's response for better formatting 
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip() ]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

# Function to load chat log safely from the portable path
def load_messages_safely():
    # Use os.path.join for cross-platform file path handling
    file_path = os.path.join("Data", "ChatLog.json")
    try:
        with open(file_path, "r") as f:
            return load(f)
    except (FileNotFoundError, Exception) as e:
        # If file is not found or corrupted, start with an empty list
        if not os.path.exists(file_path):
             with open(file_path, "w") as f:
                 dump([], f)
        
        return []

# --- Main Chatbot Logic ---
def Chatbot(Query):
    """This function sends user's query to the chatbot and returns AI response"""

    # 1. Load history (this list is used for the current conversation)
    messages = load_messages_safely()
    
    # 2. Append the users query and system context
    messages_for_api = SystemChatbot + [{"role": "system", "content": get_current_datetime()}] + messages
    messages_for_api.append({"role": "user", "content": Query})
    
    Answer = ""
    
    # 3. Request API response
    try:
        completion = client.chat.completions.create(
            # Using the fast, stable model:
            model="llama-3.1-8b-instant",
            messages=messages_for_api,
            max_tokens=1024,
            temperature=0.7, 
            stream=True, 
            stop=None 
        )
    except groq.NotFoundError as e:
        print(f"\n[ERROR] Model or API Key Issue: {e.message}")
        return "I'm sorry, the AI model is unavailable or has been decommissioned. Please check the model name."
    except Exception as e:
        print(f"\n[ERROR] Network or Client Issue: {e}")
        return "A network or client error occurred. Trying again might help."

    # 4. Process the streamed response
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            Answer += chunk.choices[0].delta.content

    Answer = Answer.replace("<\s>", "") # cleanup unwanted tokens

    # 5. Append new response to history and save log
    messages.append({"role": "assistant", "content": Answer})
    
    # Save the updated chat log using the portable path.
    with open(os.path.join("Data", "ChatLog.json"), "w") as f:
        dump(messages, f, indent=4)

    # 6. Return the formatted response.
    return AnswerModifier(Answer)


# --- Main Execution Block ---
if __name__ == "__main__":
    # Note: We are using 'python3' for execution in the terminal for better compatibility
    while True:
        user_input = input("Enter Your Question: ") 
        if user_input.lower() in ["exit", "bye", "quit"]:
            print("Exiting Chatbot Test.")
            break
        
        print(Chatbot(user_input)) 