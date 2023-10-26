# Job Interview Coach
### Mock Interview with Feedback

# LICENSE AND DISCLAIMER:
# Copyright 2023, Jozsef Szalma<
# Creative Commons Attribution-NonCommercial 4.0 International Public License 
# Gradio code was reused from / informed by: https://www.gradio.app/guides/creating-a-chatbot-fast

# Before repurposing this code for an HR use-case consider:
# OpenAI's useage policies (https://openai.com/policies/usage-policies) expliclitly prohibit:
# "Activity that has high risk of economic harm, including [...] Automated determinations of eligibility for [...] employment [...]" 

# The EU AI Act proposal (https://eur-lex.europa.eu/resource.html?uri=cellar:e0649735-a372-11eb-9585-01aa75ed71a1.0001.02/DOC_1&format=PDF) 
# contains the following language:
# "AI systems used in employment, workers management and access to self-employment,
# notably for the recruitment and selection of persons [...] should also be <b>classified as high-risk"

# KNOWN ISSUES:
# - incomplete error handling around job description, e.g. if an invalid JD URL is provided the code won't fall back to the copy-pasted JD
# - if no JD and/or CV are provided GPT-4 might on occasion ignore instructions to only ask one interview question at a time
# - the current workflow consumes a lot of tokens as the JD and the CV aren't summarized, but considered as-is for each question
# - the scraping logic breaks once the job is in the "no longer accepting applications" status

#env variables
import os

#API
import openai

#UI
import gradio as gr

#to digest the Job Description and the Resume
import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import re

#store OpenAI API key in .env file or replace right side of the equation with your key
openai.api_key = os.getenv("KEY")

#OpenAI Parameters
#I'm using two prompts here, immagine this like a two person interview panel, one conducts the interview, the other evaluates

INTERVIEWER_MODEL = 'gpt-4-0613'
INTERVIEWER_TEMPERATURE = 0.4
INTERVIEWER_TOKEN_LIMIT = 300

INTERVIEWER_PROMPT = """
    Role: 
        Interviewer in a job interview coaching application; your role is to interview the candidate. 
        Do not provide feedback, that is done after the interview by a human.
        Follow the interview script, don't ask more than one question per message.

    Interview script:
        1) Welcome the candidate
        2) Check if a CV was automatically provided by the system, ask the candidate to provide their CV if not.
        3) If the CV was provided by the system ask the candidate to confirm if you have their correct CV by showing a short summary.
        4) Check if a Job Description was automatically provided by the system, ask the candidate to provide the JD they are interviewing for if not. 
        5) If the JD was provided by the system ask the candidate to confirm if you have the correct JD by showing a short summary.
        6) Compare and contrast Candidate Resume and Job Description and ask the first clarification question from the candidate to establish overlaps and disconnects between JD and CV.
        7) Ask the 2nd clarification question from the candidate to establish overlaps and disconnects between JD and CV.
        8) Ask the 3rd clarification question from the candidate to establish overlaps and disconnects between JD and CV.
        9) Ask the candidate for their motivation to apply to this job, if not yet discussed.
        10) Thank the candidate, explain that feedback will be provided at a later stage and append to your last message {interview ended}
    """



REVIEWER_MODEL = 'gpt-4-0613'
REVIEWER_TEMPERATURE = 0.2
REVIEWER_TOKEN_LIMIT = 2000

REVIEWER_PROMPT = """
    Role:
        Job interview coach in a job interview coaching application.

    Task:
        Your role is to review a conversation between the interviewer and the candidate and provide feedback.
        Only consider job relevant questions, additional chatter (e.g. confirming data) can be ignored.
        Rate answers on a scale from 1 (worst) to 10 (best).
        Recommend an alternative answer for each question.
        Provide your response as a valid, but human readable JSON, see template:

        {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Could you please ellaborate on...",
                    "candidate_answer": "I think...",
                    "recommended_answer": "",
                    "answer_correctness_rating": 9
                }
            ],
            "overall_rating": "90%"
        }
    """
#caching additional inputs 
linkedin_jd_cache = {}
linkedin_jd = ""
candidate_cv = ""

#For the sake of simplicity I'm providing an option to scrape the JD from LinkedIn directly 
#This is probably against LinkedIn's T&Cs, so use at your own risk
#Also, the scraping logic breaks once the job is in the "no longer accepting applications" status

def extract_linkedin_jd (URL, copy_paste):
    global linkedin_jd_cache
    global linkedin_jd
    if URL:
        #Checking if the JD has already been scraped
        if URL in linkedin_jd_cache:
            print(f"Text for {URL} already loaded.")
            return linkedin_jd_cache[URL]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        response = requests.get(URL, headers=headers)
        jd = ""
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            #Finding the job title
            job_title_tag = soup.find('h1', class_='topcard__title')
            if job_title_tag:
                job_title = job_title_tag.text.strip()
                jd = jd + job_title
            else:
                jd = jd + "Couldn't find job title on LinkedIn \n"

            #Finding the company name
            company_name_tag = soup.find('a', class_='topcard__org-name-link')
            if company_name_tag:
                company_name = company_name_tag.text.strip()
                jd = jd + company_name
            else:
                 jd = jd + "Couldn't find company name on LinkedIn \n"

            # Finding the job description
            job_description_tag = soup.find('div', class_='description__text')
            if job_description_tag:
                job_description = job_description_tag.text.strip()
                jd = jd + job_description
            else:
                jd = jd + "Couldn't find job description on LinkedIn \n"
            jd = re.sub('\n+', '\n', jd)
            linkedin_jd_cache[URL] = jd

        else:
            print("Failed to retrieve the webpage. Status code:", response.status_code)
            jd = "couldn't load JD from LinkedIn"

    elif copy_paste:
        jd = copy_paste
    
    else:
        jd = "no JD provided"

    linkedin_jd = jd
    return jd


#Loading the Candidate's Resume
def load_cv (cv_pdf):
    global candidate_cv

    #converting between Gradio's feed and what pdfpluber can digest
    cv_pdf = io.BytesIO(cv_pdf)
    
    with pdfplumber.open(cv_pdf) as pdf:
        #initializing an empty string to store the extracted text
        text = ""

        #iterating over each page of the PDF
        for page in pdf.pages:
            #extracting text from the page and add it to the text string
            text += page.extract_text()
        
        #removing extra line breaks
        text = re.sub('\n+', '\n', text)
        
        candidate_cv = text

        return text

#extracting control messages from streaming text enclosed in curly braces
#this can be used, inter alia, for the interviewer to indicate the end of the interview
#TODO replace this with a more formalized solution detailed here: https://platform.openai.com/docs/guides/gpt/function-calling
def extract_control(text):
        
    pattern = r'{(.*?)}'
    match = re.search(pattern, text)
    if match:
        control = match.group().replace("{","").replace("}","")
        text_without_control = re.sub(pattern, '', text)
    else:
        control_start = text.find('{')
        if control_start != -1:
            control = text[control_start + 1:]
            text_without_control = text[:control_start]
        else:
            control = ""
            text_without_control = text

    return text_without_control, control

#this is the handler function that gets triggered when the submit button is pressed
#contains the prompt engineering logic as well
def btn_handler(message, history): 
    
    #this part handles the standard interview
    history_openai_format = []
    #adding the interviewer prompt as a system message
    history_openai_format.append({"role": "system", "content": INTERVIEWER_PROMPT})
    #adding the JD as a system message
    history_openai_format.append({"role": "system", "content": "Job Description: " + linkedin_jd})
    #adding the CV as a system message
    history_openai_format.append({"role": "system", "content": "Candidate's CV: " + candidate_cv})
    #translating the Gradio chat history into OpenAI format
    for human, assistant in history:
        history_openai_format.append({"role": "user", "content": human })
        history_openai_format.append({"role": "assistant", "content":assistant})
    history_openai_format.append({"role": "user", "content": message})

    #submitting the interviewer inference request to the API
    response = openai.ChatCompletion.create(
        model= INTERVIEWER_MODEL,
        messages= history_openai_format,
        temperature=INTERVIEWER_TEMPERATURE,
        max_tokens  = INTERVIEWER_TOKEN_LIMIT,
        stream=True,
        n = 1
    )

    partial_message = ""
    control_message = ""
    trimmed_message = ""
    #yielding the streamed message to the chat window, while ensuring control messages don't become visible
    for chunk in response:
        if len(chunk['choices'][0]['delta']) != 0:
            partial_message = partial_message + chunk['choices'][0]['delta']['content']
            trimmed_message, control_message = extract_control (partial_message)
            yield trimmed_message


    #if the interview has ended let's ask for the evaluation
    if control_message == "interview ended":
        print("starting eval")

        eval_prompt = []
        history_adj_format = []
        #composing the eval prompt
        eval_prompt.append({"role": "system", "content": REVIEWER_PROMPT})
        eval_prompt.append({"role": "system", "content": "Job Description: " + linkedin_jd})
        eval_prompt.append({"role": "system", "content": "Candidate's CV: " + candidate_cv})
        
        #transforming the chat history to ensure the reviewer model don't get confused and continue the interview
        for human, assistant in history:
            history_adj_format.append({"role": "candidate", "content": human })
            history_adj_format.append({"role": "interviewer", "content":assistant})
        eval_prompt.append({"role": "system", "content": str(history_adj_format).replace("\"","")})

        #making the review inference call to the API
        response = openai.ChatCompletion.create(
            model= REVIEWER_MODEL,
            messages= eval_prompt,
            temperature= REVIEWER_TEMPERATURE,
            max_tokens  = REVIEWER_TOKEN_LIMIT,
            stream=True,
            n = 1
        )

        #continuing the streaming where we left off
        partial_message = trimmed_message + r"<br>"
        for chunk in response:
            if len(chunk['choices'][0]['delta']) != 0:
                partial_message = partial_message + chunk['choices'][0]['delta']['content']            
                yield partial_message   


chat_tab = gr.ChatInterface(btn_handler).queue()

jd_tab = gr.Interface(
    fn=extract_linkedin_jd, 
    inputs=[
            gr.Textbox("", label="Job Description LinkedIn URL"),
            gr.Textbox("", label="or copy-paste Job Description here")
        ], 
    outputs=[
            gr.Textbox()
        ],
    allow_flagging="never"
    )

cv_tab = gr.Interface(
    fn=load_cv, 
    inputs=[
            gr.File(type='binary'),
        ], 
    outputs=[
            gr.Textbox()
        ],
    allow_flagging="never"
    )


demo = gr.TabbedInterface([cv_tab, jd_tab, chat_tab], ["CV Upload", "Job Description", "Interview"]).queue()


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")