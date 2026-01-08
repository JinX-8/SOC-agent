import cohere # Import cohere library for AI services
from rich import print # Import rich library for enhanced terminal output
from dotenv import dotenv_values # Import python-dotenv to manage environment variables

# --- Initialization ---
# Load environment variables from .env file
env_vars = dotenv_values(".env")

# Retrieve API key from environment variables
COHERE_API_KEY = env_vars.get("COHERE_API_KEY")

# Create a Cohere client instance using the API key
co = cohere.Client(api_key=COHERE_API_KEY)

# Define a list of recognized function keywords for task categorization. (FIXED COMMA)
funcs = [
   "exit", "general", "realtime", "open", "close", "play", "generate image",
   "system", "content", "google search", "youtube search", "reminder"
]

# Initialize an empty list to store user messages
messages = []

# --- Preamble (AI's Instructions) ---
preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation.
*** Do not answer any query, just decide what kind of query is given to you. ***

-> Respond with 'general ( query )' if a query can be answered by an LLM model and doesn't require real-time data, or if the query is incomplete (e.g., 'who is he?'). Also use for time, day, date, etc.
-> Respond with 'realtime ( query )' if a query requires up-to-date information (e.g., 'who is indian prime minister') or is asking about any specific individual or entity.
-> Respond with 'open (application name or website name)' if a query is asking to open any app or website.
-> Respond with 'close (application name)' if a query is asking to close any application.
-> Respond with 'play (song name)' if a query is asking to play any song on YouTube.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate an image.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder.
-> Respond with 'system (task name)' for muting, unmute, volume control, etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content (application, code, email) about a specific topic.
-> Respond with 'google search (topic)' if a query is asking to search on Google.
-> Respond with 'youtube search (topic)' if a query is asking to search on YouTube.

*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye jarvis.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""

# --- Chat History for Context ---
ChatHistory = [
    {"role": "User", "message": "how are you?"}, {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"}, {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."}, 
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
    {"role": "User", "message": "open chrome and firefox"}, {"role": "Chatbot", "message": "open chrome, open firefox"},
    {"role": "User", "message": "what is today's date and by the way remind me that i have a dancing performance on 5th aug at 11pm"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11:00pm 5th aug dancing performance"},
    {"role": "User", "message": "chat with me."}, {"role": "Chatbot", "message": "general chat with me."}
]

# --- Main Decision Function ---
def FirstLayerDMM(prompt: str = "test"):
    # Add the user's query to the messages list (for general conversation history if needed later)
    messages.append({"role": "user", "content": f"{prompt}"})

    # Create a streaming chat session with the Cohere model.
    Stream = co.chat_stream(
        model="command-r-plus-08-2024", 
        message=prompt,         
        temperature=0.7,        
        chat_history=ChatHistory, 
        prompt_truncation='OFF',  
        connectors = [],
        preamble = preamble
    )
    
    response_text = ""
    for event in Stream:
        if event.event_type == "text-generation":
            response_text += event.text 

    # Clean the response and split multiple tasks
    response_text = response_text.replace("\n", " ")
    
    # Split the response by comma and space for multiple tasks (e.g., 'open chrome, open firefox')
    tasks = [task.strip() for task in response_text.split(",")]
    
    filtered_tasks = []

    # FILTER tasks against the defined function keywords
    for task in tasks:
        is_valid = False
        for func_keyword in funcs:
            if task.startswith(func_keyword):
                filtered_tasks.append(task)
                is_valid = True
                break  # Stop checking this task once a keyword is found
        
    return filtered_tasks # Return the list of validated tasks

# --- Main Execution Block (FIXED loop and print) ---
if __name__ == "__main__":
    while True:
        user_input = input(">>> ")
        if user_input.lower() in ["exit", "bye", "quit"]:
            print("Exiting DMM.")
            break
        
        # Execute the DMM and print the resulting list of tasks
        tasks_to_execute = FirstLayerDMM(user_input)
        print(tasks_to_execute)