# Job Interview Coach
### Mock Interview with Feedback

![image](https://github.com/jozsefszalma/interview_coach_GPT-4/assets/96535232/c43b59c5-590f-4a81-a1f9-bdea7dc50c69)


# Setup
Clone repo into a folder of your choice.<br>

### With Docker
run in the same folder: <br>
* docker build -t interview_bot . 
* docker run -p 7860:7860 --env KEY=your_openai_api_key interview_bot <br>
navigate to http://127.0.0.1:7860/ with your browser <br><br>

### From Notebook
* create a Python 3.9 venv or conda environment <br>
* install dependencies e.g. pip install -r requirements.txt <br>
* set up your OpenAI API key as "KEY" environment variable (e.g. via .env file if using VSCode) <br>
* As the UI might not fully render in a small window within an IDE I recommend connecting to the URL returned by Gradio, e.g. the default http://127.0.0.1:7860/ with your browser <br><br>

### Usage
provide your CV pdf on the left-most tab, provide the Job Description on the middle tab and begin the interview on the right-most tab. <br><br>


### LICENSE AND DISCLAIMER:
Copyright 2023, Jozsef Szalma<br>
Creative Commons Attribution-NonCommercial 4.0 International Public License <br>
Gradio code was partially reused from / informed by [this guide](https://www.gradio.app/guides/creating-a-chatbot-fast)

Before repurposing this code for an HR use-case consider: <br>
* OpenAI's [useage policies](https://openai.com/policies/usage-policies) expliclitly prohibit:<br>
"Activity that has high risk of economic harm, including [...] Automated determinations of eligibility for [...] employment [...]" <br>

* The [EU AI Act proposal](https://eur-lex.europa.eu/resource.html?uri=cellar:e0649735-a372-11eb-9585-01aa75ed71a1.0001.02/DOC_1&format=PDF) contains the following language:<br>
"AI systems used in employment, workers management and access to self-employment,
notably for the <b>recruitment and selection of persons</b> [..] should also be <b>classified as high-risk</b>"

### KNOWN ISSUES:
* incomplete error handling around job description, e.g. if an invalid JD URL is provided the code won't fall back to the copy-pasted JD
* if no JD and/or CV are provided GPT-4 might on occasion ignore instructions to only ask one interview question at a time
* the current workflow consumes a lot of tokens as the JD and the CV aren't summarized, but considered as-is for each question
* the scraping logic breaks once the job is in the "no longer accepting applications" status
