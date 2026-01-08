import asyncio
from random import radiant
from PIL import Image
import requests
from dotenv import get_key
import os
from time import sleep 


#Function to open and display images based on the given prompt
def open_image(prompt):
    folder_path = r"Data"
    prompt = prompt.replace(" ", "_")

#generate the file names for images
    Files = [f"{prompt}{i}.jpg" for i in range(1,5)]

    for jpg_files in Files:
        image_path = os.path.join(folder_path, jpg_files)
        try:

            img = Image.open(image_path)
            print(f"opening Image: {image_path}")
            img.show()
            sleep(1)

        except IOError:
            print(f"Unabel to open image: {image_path}. File may not exist.")

#API details  for the  hugging face  stable diffusion model
API_URL = "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
headers = {"Authorization": f"Bearer {get_key('.env', 'HUGGINGFACE_API_KEY')}"}

# Async Function to send a query to the hugging face api
async def query(payload):
    response = await asyncio.to_thread(requests.post,API_URL, headers=headers , json=payload)
    return response.content

async def generate_image(prompt : str):
    task=[]


    for _ in range(4):
        payload = {
            "inputs": f"{prompt}, quality high , detailed, 4k, trending on artstation  ",
            
        } 
        task = asyncio.create_task(query(payload))
        task.append(task)
    #wait for all tasks to complete
    image_bytes_list = await asyncio.gather(*task)

    #save the images to the Data folder
    for i, image_bytes in enumerate (image_bytes_list):
        with open(f"Data/{prompt.replace(' ', '_')}{i+1}.jpg", "wb") as f:
            f.write(image_bytes)

#wrapper function to manage image generation
def GenerateImages(prompt: str):
    asyncio.run(generate_image(prompt))
    open_image(prompt)

while True:

    try:

        #read the status and prompt from the data file
        with open(r"Frontend\ Files \ ImageGeneration.data ","r" ) as f:
            Data: str = f.read()

            Prompt , Status = Data.split(",") 


            #if the status indicates an image generation request
            if Status == "True":
                print("Generating Image...")
                ImageStatus = GenerateImages(prompt=Prompt)



                #reset the status in the field after generating images
                with open(r"Frontend\ Files \ ImageGeneration.data","w") as f:
                    f.write("False,False")
                    break

            else:
                sleep(1)


    except Exception as e:
        print(e)
        
        
