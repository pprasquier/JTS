# Overview
**JTS (for Job Tracking System)**  is an open-source tool designed to streamline the job application process. By harnessing the power of AI, JTS enables users to create personalized cover letters tailored to specific job postings. It takes into account the nuances of the job description, the applicant's resume, previously crafted cover letters, and additional insights collected systematically. The ultimate goal is to increase the chances of your application being noticed by recruiters by providing a cover letter that addresses the recruiter's needs while showcasing your relevant experience.

# Key features
- Use OpenAI's LLM or any local LLM through LM studio or Ollama
- Connect to an Airtable database in which you will be able to track your job applications
- Export your cover letters in a templated PDF format
- Export your resumes in a templated PDF format from a structured Airtable database, including a customized summary for each job application
- Export contextual data in the form of questions/answers from Airtable database
- And much more

# Target audience
This project is currently intended for users with some technical experience. Installation and usage require familiarity with Python, development tools, and CLI commands.

# Installation
## Prerequisites
Ensure the following applications are installed on your computer:
- **Python 3.9+**
- **[Poetry](https://python-poetry.org/)**: to handle Python packages
- **TeX engine**: Such as TeX Live, for PDF generation. 
- **[wkhtmltopdf](https://wkhtmltopdf.org/index.html)**
- **IDE**: Visual Studio Code or similar (Optional)
- **LM Studio** or **Ollama**: For serving local LLMs (Optional)

## Clone the source repository
Download or clone the content from [GitHub](https://github.com/pprasquier/JTS) into a new local repository

## Install Python dependencies
``` Terminal
poetry update
```

## Activate the Poetry environment
``` Terminal
poetry shell
```

## Environment variables
Set the following environment variables up:
- **OPENAI_API_KEY** : OpenAI API key (if using OpenAPI as LLM for one of the requests)
- **AIRTABLE_API_KEY** : Airtable Private Access Token (Optional - if using the connection with Airtable)
- **TAVILY_API_KEY** : Linked to your https://tavily.com/ account. Used to enrich job post with external data (optional). Not yet fully implemented. 

## Airtable integration
Airtable is a cloud database application that provides users with an easy-to-use immediately available way to store/edit records. 
It is optional but connecting it to JTS adds multiple useful features to JTS.
In order to connect the pre-configured database to JTS: 
1. Create a free account or log into your [airtable account](https://airtable.com/invite/r/hUEhHdoc)   
2. Use the [following template](https://www.airtable.com/universe/expaZeJeBH8JctlsZ/jts-connected-database?_gl=1%2Abcj3uk%2A_gcl_au%2ANTQwODE5MTg1LjE3MjM4NDUyMTQ.%2A_ga%2AMTQyMzc4NDM3MS4xNzA4Njk4MzMz%2A_ga_HF9VV0C1X2%2AMTcyMzg0ODU2NS4xNTIuMS4xNzIzODQ5MDIyLjQ4LjAuMA..) and copy it to your account
3. Duplicate `settings_files\0_customizable_airtable_settings.json` and rename the new file into a name not starting with 0 (to prevent it from being overwritten when pulling from git) 
4. In the new file, update the following values:
- *use_airtable*:**True**
- All the keys where "type" is "Airtable" and key ends in "table_id" -> the **tbl_...** Airtable id of the corresponding table 
5. Optionally, if you'll be using the feature to download knowledge data from Airtable:
- *use_airtable_knowledge*:**True**
- All the keys where "type" is "Airtable_Table_Knowledge" and key ends in "table_id" -> the **tbl_...** Airtable id of the corresponding table  
6. Optionally, if you'll be using the feature to download structured resume data from Airtable:
- *use_airtable_resume*:**True**
- All the keys where "type" is "Airtable_Table_Knowledge" and key ends in "table_id" -> the **tbl_...** Airtable id of the corresponding table  

# Customization
## Personal information
The more information the AI knows about you, the more customized the cover letters will be. 
JTS offers you two ways of feeding it information about you. 

### Your resume
This is the most important document that the AI will use to customize your cover letters. 
The default storage path for that is:  `private\embeddings\resume\input`
Feel free to leave out of this anything that you wouldn't want to be sent to the LLM (e.g., your personal information) and/or that doesn't add anything relevant in the context of a cover letter. And make sure its formatting is as simple as possible to be fully parsed by the AI.
PDF format

### Relevant information
You can provide the AI with additional relevant information by using the format of a .csv Questions and Answers file. 
Use it to add information that might become handy to customize your cover letters. 
Default storage path: `private\embeddings\knowledge\input`
You can find an example of such a file in: `example_files\knowledge.csv`
CSV format

### Example cover letters
If you have already written good cover letters, you can store their contents so as to be used as example by the AI. 
Save them as .txt files inside of `private\cover_letters`
TXT format

### Example summaries
If you want to be able to customize the executive summary of your resume, you can provide the AI with examples of relevant summaries in: `private\summaries`
TXT format


## Templates
### Cover letters
Once you're satisfied with the body of your personalized cover letter, you can ask JTS to generate the corresponding PDF document using a customizable format like the one in: `example_files\cover_letter_template.html`
Store your own version of such an html template in: `private\templates\cover_letter_template.html`
HTML format (Jinja-enabled)

### Resume
If you want to be able to generate resumes from Airtable and include customized summaries for each job application, you'll first have to store a resume template like the one in: `example_files\resume_template.html` into: `private\templates\resume_template.html`
HTML format (Jinja-enabled)

# Getting started
Once installation is complete and the necessary files are in place, launch JTS:
The default settings will use OpenAI's api for all AI jobs. In order to change the default settings, refer to the [LLM](#llm). 

## Launching the app
Launch a terminal from the root of the application and run:
 ```Terminal
 python3 jts.py
 ```

## First-Time Setup
When launching the application for the first time, you'll need to build the local vector stores with the provided personal data (see [How to customize the app](#personal-information)). 
In order to do so, Navigate to `Administration > Load/replace embeddings with content of input directories`.
From them on, you'll only need to perform this task when you update the contents of the resume or knowledge files. 

## Adding a job post
### Through Airtable
1. In your Airtable instance, add a new record in table *Job*. Only the field *Full job description* is required. You can store the *Source* as well to be able to easily access the application page. 
2.  `Manage job posts > Load from Airtable`
This will download all jobs with status = "For interpretation", create a file for each of them in `private\history`, link it to its Airtable row and parse the job description through AI. 

### Through json files
1. Navigate to `Manage job posts > Create a blank job post`
2. When asked for a name, enter a name for this job post
3. JTS will create a json file with that name in `private\history`. Open it and replace the value of key *initial_job_post* with the strigified content of the job post. Save the file. 
4. In the CLI, select option `Load existing job post`
5. Enter the name that you've just selected. 
This will load the specified job post. 

### By scraping a web page
1. Navigate through the following menu: `Manage job posts > Scrape a web page`
2. Enter the url of the job post's page
If a parser definition is available for this web site in `web_parser_definitions.csv`, JTS will attempt to scrape it and load it into the system. 


# Job post actions
Once a post is loaded, a few different actions become available in the CLI. 

## Add relevant information
This allows you to add information specifically related to this job post, which will ultimately help the UI customize the cover letter. 
E.g.: "I have personally used XXX product for the past 10 years."

## Generate cover letter body
### Basic
The most straightforward way to generate a cover letter using your personal data is to simply launch `Generate quick cover letter`

### Advanced
The more advanced method provides you with more control as to the process going into generating the cover letter. It is separated into different (AI or deterministic) steps to allow you to manually review and update AI's "thought process" by checking and updating the job's individual json file, available in `private\history`. After each change that you've performed, in order to update JTS' memory, you'll need to run ** Refresh from file **. 

- Step 1. Parse job post
This process parses the raw job post into a structured list of elements commonly found in job posts. 

- Step 2. Derive salient points 
AI will analyze the job post to identify what it believes are the most relevant requirements.  

- Step 3. Collect insights from embeddings
Once salient points have been derived, AI will try to match them with insights from your resume and knowledge base. 

- Step 4. Generate cover letter (advanced)
This process will generate a cover letter using the insights from Step 3. 

## Modify the cover letter with AI
** Edit cover letter content with the help of AI ** will open a conversation with AI based on the current body of your cover letter. You'll then be able to tweak it with the help of AI.   

## Generate a cover letter PDF
The processes above only generate the body of the cover letter, which you can manually update within the job's individual json file, available in `private\history` (field "cover_letter.current_body").
To generate a PDF file for your cover letter, customized for the organization and position, just launch ** Save custom resume **
This will generate a PDF in the `private\applications` directory. 

## Generate an executive summary
`Generate an executive summary` will customize an executive summary of your resume for this job post. 

## Save custom resume
If you have activated the Airtable connection and the Airtable resume feature, you'll be able to generate a resume for this specific job post with: 
- The customized executive summary
- Optionally, the content of the job post itself. This MIGHT trick ATS into giving your resume more weight and requires you storing a template of your resume like the one in `example_files\resume_template_with_job_post.html` into `private\templates\resume_template_with_job_post.html`

## Store cover letter as example
This option adds your current job post's cover letter to the list of examples that are to be used in subsequent AI cover letter generations. It automatically creates the corresponding .txt file in `private\cover_letters`

# Settings
JTS uses [Prefy](https://pypi.org/project/prefy/) to manage settings. 

The file `settings_files\0_0_all_default_settings.json` contains all the settings that the app may need. If you expect to contribute to the JTS project by pushing your code, DO NOT CHANGE ITS PREDEFINED VALUES. 

If you want to run the app with different sets of settings, you can override the default settings by just adding new JSON settings files in the *settings* folder and naming them with a prefix superior to 0. The new files don't have to contain values for all settings: just for those you wish to override. 

# LLM
The app is set by default to run with the OpenAI api. 

However, you can run all AI queries locally through [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.com/) after loading the model of your choice and running it as a local server. 

In order to indicate the types of queries you want to run locally, create a new settings file with an entry for each of the entries (in the settings\0_XXX files) where type = "Models" and key ends with "_base_url" and enter, as value, the url of your local server. 

For instance: 
```json    
    {
        "type":"Models",
        "key":"job_parse_base_url",
        "description":"LLM model's url for parsing job offers. Leave blank to use OpenAI or insert your local server's URL.",
        "value":"http://localhost:1234/v1"
    }
```

In order to use Ollama, you'll also have to set the *llm_api* setting to **Ollama**, instead of **ChatOpenAI** (which applies to both OpenAI and LM Studio).

## Notes
### Model considerations
- Local model **TheBloke - Claude2 Alpaca Q8** is unreliable when requested a specific json format and doesn't parse jobs well
- Passabe results across the board have been obtained with **una cybertron v2b Mistral Q5KM**
- **Llama3** is good for classification and rag. Cover letter generation and updates perform poorly.

# Known issues
## Unknown characters in input files
Unknown characters in input files are not well caught (e.g., by CSVLoader). Make sure your files are completely Unicode-compliant. 
Example of characters to cause issues: “” 

## [WinError 126] The specific module could not be found. Error loading "...\torch\lib\fbgemm.dll” or one of its dependencies"
On Windows, this issue can generally be solved by installing https://www.dllme.com/dll/files/libomp140_x86_64 in the `C:\Windows\System32` directory

# Contribute to this project
JTS is a work in progress and will gladly receive your suggestions/changes. Please, see `contributing.md` for details.