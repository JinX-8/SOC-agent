import os
from googlesearch import search
from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values

#load environment variables from .env file
env_vars = dotenv_values(".env")

#retrieve specific environment variables
Username = env_vars.get("USERNAME")
AssistantName = env_vars.get("ASSISTANT_NAME")
GROQ_API_KEY = env_vars.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {AssistantName} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""

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

# function to perform a google search and format the results
def GoogleSearch(query):
    results = list(search(query , advanced=True , num_results=5))
    answer = f"The search results for '{query}' are :\n [start]\n"

    for i in results:
        answer += f"Title ; {i.title}\nDescription : {i.description}\n\n"

    answer += "[end]"
    return answer
# Function to modify the chatbot's response for better formatting
def AnswerModifier(answer):
    lines = answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip() ]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer
#predefined system message for the chatbot and initial user message
SystemChatbot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hello! How can I assist you today?"},
]

#fumction to get real-time date and time
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

#function to hanndle real-time search queries
def RealtimeSearchEngine(prompt):
     global SysytemChatbot, messages 
     with open(os.path.join("Data", "ChatLog.json"), "r") as f:
        messages = load(f)
     messages.append({"role": "user", "content": f"{prompt}"})

     SystemChatbot.append({"role": "system", "content": GoogleSearch(prompt)})

     #generate response from the Groq API
     completion = client.chat.completions.create(
            # Using the fast, stable model:
            model="llama-3.1-8b-instant",
            messages=SystemChatbot + [{"role": "system", "content": get_current_datetime()}] + messages,
            max_tokens=1024,
            temperature=0.7, 
            stream=True, 
            stop=None 


     )
     answer = ""
     for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            answer += chunk.choices[0].delta.content

     answer = answer.replace("<\s>", "") # cleanup unwanted tokens

    # 5. Append new response to history and save log
     messages.append({"role": "assistant", "content": answer})  
     with open(os.path.join("Data", "ChatLog.json"), "w") as f:
        dump(messages, f, indent=4)

    # 6. Return the formatted response.
     SystemChatbot.pop()  # remove the last system message to keep context relevant
     return AnswerModifier(answer)
if __name__ == "__main__":
    while True:
        prompt = input("Enter your query ")
        print(RealtimeSearchEngine(prompt))