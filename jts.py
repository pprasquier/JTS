import logging
import os
import requests
import types

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
# pip install langchain-openai
from langchain.memory import ConversationBufferMemory
from job_post import JobPost, create_job_from_file
from utils import *
from templating import *
from prefy import PreferencesWrapper
from langchain_core.output_parsers import StrOutputParser
from scraper import Page
from rich import print
from openai import BadRequestError

#Menu with submenus
menu_level=types.SimpleNamespace()
menu_level.HOME="Home"
menu_level.ADMINISTRATION="Admininstration"
menu_level.RESUME="Resume"
menu_level.JOB="Manage job posts"
menu_level.SETTINGS="Settings/Personal files"
menu_level.APPLICATION="Manage app / context data"

#Menu option types
FUNCTION="function"
MENU="menu"
INPUT="input"

#Menu actions
BACK="back"
EXIT="exit"

#UI deocration
HIGHLIGHT=' ********** '

OPTION_TRUE=[True,1,"Yes","y","Y","1","true","True"]

os.environ["TOKENIZERS_PARALLELISM"] = "false" # workaround for HuggingFace/tokenizers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')


class Status:
    pass

class MenuOption:
    def __init__(self, name,order, type='function', context=None,input_list=[]) -> None:
       self.name = name
       self.type = type 
       self.context = context
       self.order = order
       self.input_list = input_list

class Conversation(PreferencesWrapper):
    def __init__(self) -> None:
        super().__init__()
        self.memory = ConversationBufferMemory() 
        self.conversation_llm=instantiate_settings_llm('conversation')
        self.conversation_prompt=PromptTemplate(
            template=self.settings.conversation_prompt,
            input_variables=["input","history"]
        )
        self.conversation_chain = self.conversation_prompt | self.conversation_llm | StrOutputParser()
        self.memory.memory_key = "chat_history"
        self.memory.return_messages = True
        self.memory.load_memory_variables({})
        self.job=None
        self.memory_status=Status()
        self.back_menu=menu_level.HOME
        self.update_conversation_options(menu_level.HOME)
    def make_comment(self, question: str,store_history=True):
        response = self.conversation_chain.invoke({"history":self.memory.chat_memory,"input":question})
        
        if store_history: 
            self.memory.chat_memory.add_user_message(question)
            self.memory.chat_memory.add_ai_message(response)
        return(response)
    
    def collect_user_input(self,back_menu=None):
        while True:
            try:   
                global FUNCTION
                global INPUT
                global MENU
                
                if hasattr(self, 'job') and self.job is not None:
                    if hasattr(self.job, 'history') and self.job.history is not None:
                        if hasattr(self.job.history, 'id') and self.job.history.id is not None:
                            print(HIGHLIGHT,self.job.history.id,HIGHLIGHT)
                                        
                print("Select an option in the menu below.")
                for index, option in enumerate(self.option_list):
                    print(f"[bold]{index}. {option.name}[/bold]")
                user_input = input("[MENU] > ")

                selected_option=self.option_list[int(user_input)]
                
                if selected_option.type==FUNCTION:
                    if selected_option.input_list.__len__()>0:
                        print("Please enter the value for: ") 
                        option_input_list=[]
                        for index, input_setting in enumerate(selected_option.input_list):
                            prompt="["+input_setting+"] > "
                            setting_value=input(prompt)
                            if setting_value =='':
                                setting_value=None
                            option_input_list.append(setting_value)
                        args_dict=dict(zip(selected_option.input_list,option_input_list))
                        selected_option.context(**args_dict)
                    else:
                        selected_option.context()
                if selected_option.type==MENU:                  
                    self.update_conversation_options(target=selected_option.context)
                    
                # response = self.ask_question(user_input)
                #print("AI: "+response)       
            except BadRequestError as e:
                print("Please check that the LLM is set up correctly and try again.")
                continue
                            
            except ValueError as e:
                print("Please type a number")
                continue
            except IndexError as e:
                print("This option does not exist. Please try again")
                continue
            except Exception as e:
                logging.error('Error {} .'.format(e))
                raise Exception
     
    def update_conversation_options(self, target=None):
         try:

            exit=MenuOption(name='Exit', order=0, type=FUNCTION,   context=self.exit)
            option_list=[exit]
            match target:
                case menu_level.HOME | None:
                    self.back_menu=menu_level.HOME
                    option_list.append(MenuOption(name=menu_level.ADMINISTRATION, order=10, type=MENU,context=menu_level.ADMINISTRATION))
                    if self.settings.use_airtable_resume:
                        option_list.append(MenuOption(name=menu_level.RESUME, order=15, type=MENU,context=menu_level.RESUME))
                    option_list.append(MenuOption(name=menu_level.JOB, order=20, type=MENU,context=menu_level.JOB))
                    option_list.append(MenuOption(name=menu_level.SETTINGS, order=30, type=MENU,context=menu_level.SETTINGS))
                case menu_level.ADMINISTRATION:
                    self.back_menu=menu_level.HOME
                    option_list.append(MenuOption(name='Load/replace embeddings with content of input directories',order=30,type=FUNCTION,context=self.replace_embeddings))
                    if self.settings.use_airtable_knowledge:
                        option_list.append(MenuOption(name='Retrieve knowledge from Airtable',order=10,type=FUNCTION,context=self.retrieve_knowledge))
                    option_list.append(MenuOption(name='Load anonymized resume into embeddings input directory',order=25,type=FUNCTION,context=self.load_anonymized_resume_into_embeddings))
                    option_list.append(MenuOption(name='Display content of the combined vector store', order=40, type=FUNCTION,context=self.display_combined_vector))
                    option_list.append(MenuOption(name='Communicate with knowledge/resume vector store', order=50, type=FUNCTION,context=self.communicate_with_vector))
                case menu_level.RESUME:
                    option_list.append(MenuOption(name='Retrieve resume data from Airtable',order=20,type=FUNCTION,context=self.retrieve_resume_data,input_list=['language']))
                    option_list.append(MenuOption(name='Save generic resume ',order=22,type=FUNCTION,context=self.save_resume,input_list=['basename']))
                    
                case menu_level.JOB:
                    self.back_menu=menu_level.HOME
                    option_list.append(MenuOption(name='Scrape a web page', order=10, type=FUNCTION,context=self.scrape_page,input_list=['url']))
                    option_list.append(MenuOption(name='Import a job post from a file',order=18,type=FUNCTION,context=self.create_job_from_file,input_list=['filepath','source']))
                    option_list.append(MenuOption(name='Create a blank job post', order=15, type=FUNCTION,context=self.create_blank_job_file,input_list=['name']))
                    if self.settings.use_airtable: option_list.append(MenuOption(name='Load from Airtable', order=20, type=FUNCTION, context=self.load_jobs_from_airtable))

                    if self.job is not None:
                        option_list.append(MenuOption('Load/update current job post',order=10,type= FUNCTION, context=self.load_job_post))
                        option_list.append(MenuOption(name='Release job post',order=200,type= FUNCTION, context=self.release_job_post))
                        option_list.append(MenuOption(name=menu_level.APPLICATION, order=100, type=MENU,context=menu_level.APPLICATION))

                    else:
                       option_list.append(MenuOption('Load existing job post',order=10,type= FUNCTION, context=self.load_job_post,input_list=['job_post_id']))
                case menu_level.APPLICATION:
                    self.back_menu=menu_level.JOB
                    option_list.append(MenuOption(name='Add relevant information', order=5, type=FUNCTION,context=self.add_personal_connection,input_list=['text']))
                    option_list.append(MenuOption(name='Run multiple processes', order=6, type=FUNCTION,context=self.run_multiple_processes,input_list=['run_parse','run_salient_points','run_insights','run_cover_letter','run_save_pdf','run_generate_summary','run_customize_resume']))
                    option_list.append(MenuOption(name='Refresh from file', order=7, type=FUNCTION,context=self.job.refresh_history_from_file))
                    if self.job.history.status.has_raw_post:
                        parse=MenuOption(name='Parse job post',order=10, type=FUNCTION, context=self.job.parse_job_post)
                        option_list.append(parse)
                        option_list.append(MenuOption('Generate an executive summary',order=60,type= FUNCTION, context=self.job.generate_summary))

                    if self.job.history.status.is_parsed:
                        option_list.append(MenuOption('Derive salient points',order=20,type= FUNCTION, context=self.job.derive_salient_points))
                    if self.job.history.status.has_salient_points:
                        option_list.append(MenuOption('Collect insights from embeddings',order=30,type= FUNCTION, context=self.get_relevant_insights,input_list=['max_nb_of_points','skip_insighted_points']))
                   
                    option_list.append(MenuOption(name='Generate cover letter (advanced)',order=50,type= FUNCTION, context=self.job.generate_cover_letter))
                    quick_cl=MenuOption('Generate quick cover letter', order=5, type=FUNCTION, context=self.job.generate_quick_cover_letter)
                    option_list.append(quick_cl)
                    option_list.append(MenuOption('Save custom resume',order=80,type= FUNCTION, context=self.save_custom_resume,input_list=['include_job_post']))
  
                    if self.job.history.status.has_cover_letter:
                        display_cl=MenuOption(name='Display cover letter', order=60,type=FUNCTION, context=self.display_cover_letter)
                        option_list.append(display_cl)
                        edit_cl=MenuOption('Edit cover letter content with the help of AI', order=70, type=FUNCTION, context=self.edit_cover_letter)
                        option_list.append(edit_cl)
                        option_list.append(MenuOption(name='Save cover letter', order=80, type=FUNCTION, context=self.job.save_cover_letter))
                        option_list.append(MenuOption(name='Store cover letter as example', order=90, type=FUNCTION,context=self.job.store_cover_letter_as_example))
            
                case menu_level.SETTINGS:
                    self.back_menu=menu_level.HOME
                    option_list.append(MenuOption(name='Check the value of a setting', order=100, type=FUNCTION, context=self.check_setting_value,input_list=['setting_name']))    
                    option_list.append(MenuOption(name='Refresh user settings', order=5, type=FUNCTION,context=self.refresh_user_settings))
                    
            
            if target is not None:
                    option_list.append(MenuOption(name='Back', order=1000, type=MENU, context=self.back_menu))
            unique_list=list(set(option_list))
            self.option_list=sorted(unique_list, key=lambda x: x.order)
            
            return self.option_list
         except Exception as e:
          logging.error('Error {} .'.format(e))
          raise Exception

    def exit(self):
        print("Exiting...")
        exit()
        
    def load_job_post(self,job_post_id=None):
        # Creates a JobPost object or loads an existing one to the conversation
        try:
            if job_post_id is not None:
                self.job=JobPost(file_id=job_post_id,settings=self.settings)
            else:
                self.job.load_job_post()
                
            self.clear_memory()
            self.back_menu=menu_level.JOB
            self.update_conversation_options(menu_level.APPLICATION)
            return self.job
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
    
    def display_cover_letter(self):
        try:
            if self.job.history.status.has_cover_letter:
                print(self.job.history.cover_letter.current_body)
            else:
                print("No cover letter available")
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
     
    def edit_cover_letter(self):
        try:
            # Add job post to conversation memory
            if self.job.history.status.is_parsed:
                job_details=str(export_json_attributes(self.job.history.job_characteristics))
                node_name='parsed_job_post'
            elif self.job.history.status.has_raw_post:
                job_details=self.job.history.raw_post
                node_name='raw_job_post'
            else:
                print("No job post available")
                return
            self.add_to_memory(message=job_details,is_user_message=False,name=node_name)

            # Add cover letter to conversation memory
            if not self.job.history.status.has_cover_letter:
                print("No cover letter available")
                return
            self.add_to_memory(message=self.job.history.cover_letter.current_body,is_user_message=False,name="cover_letter")                        
            response=self.job.history.cover_letter.current_body
            
            #Run the REPL loop
            while True:
                print(HIGHLIGHT,"Write your comments below. To go back, type {BACK} to return to the main menu and save the cover letter in its current state")
                user_comment=input(">[Human]: ")
                if user_comment.lower()==BACK:
                    self.job.history.cover_letter.current_body=response
                    self.job.update_history()
                    return
                response=self.make_comment(question=user_comment,store_history=True)
                print(f">[AI]: {response}")
                
        except Exception as e:
            logging.error('Error {} .'.format(e))
        raise Exception
    
    def save_cover_letter(self):
        try:
            if not self.job.history.status.has_cover_letter:
                print("No cover letter available")
                return
            
            self.job.save_cover_letter()
            print(f'Cover letter saved to: {self.job.history.cover_letter.directory}')
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
     
    def save_custom_resume(self,include_job_post):
        try:
            if include_job_post in OPTION_TRUE:
                template_file_path=self.settings.resume_template_with_job_post
            else:
                template_file_path=self.settings.resume_template
            
            custom_resume=self.job.save_custom_resume(template_file_path)
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
     
    
    def release_job_post(self):
        try:
            self.job=None
            self.clear_memory()
            self.update_conversation_options(menu_level.JOB)

        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
    
    def add_to_memory(self, message: str,is_user_message=False,name=None):
        #Check if the message is already in conversation memory. If not, add it. If it is, do not add it again.
        
        if name is not None:
            if not hasattr(self.memory_status, name) or getattr(self.memory_status, name) is None or getattr(self.memory_status, name)==False: 
                message="<"+name+">\n"+message+"\n</"+name+">"
                setattr(self.memory_status, name, True)
            else:
                logging.info("Skipping message {} as it is already in memory").format(name)
                return
            
        if is_user_message:
            self.memory.chat_memory.add_user_message(message)            
        else:
            self.memory.chat_memory.add_ai_message(message)
        logging.info("Message added to conversation memory: {}".format(message))
    
    def clear_memory(self):
        self.memory.clear()
        self.memory_status=Status()
        logging.info("Conversation memory cleared")
    
    def add_personal_connection(self,text):
        try:
            self.job.add_personal_connection(text)
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
    
    def create_blank_job_file(self,name=None):
        try:
            self.job=JobPost(file_id=name,create_input_history_file=True,settings=self.settings)
            self.job.history.source=self.settings.blank_source_text
            self.job.history.initial_job_post=self.settings.blank_source_initial_post
            self.job.update_history()
            print(f"Job post file created: {self.job.file.filepath}")
            return self.job.file.filepath
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
     
    def create_job_from_file(self,filepath,source=None):
        try:
            self.job=create_job_from_file(filepath=filepath,source=source)
            return self.job
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception

    def run_multiple_processes(self,run_parse,run_salient_points,run_insights,run_cover_letter,run_save_pdf,run_generate_summary,run_customize_resume):
        try:
            function_list=[]
            if run_parse in OPTION_TRUE:
                function_list.append(JobPost.parse_job_post.__name__)
            if run_salient_points in OPTION_TRUE:
                function_list.append(JobPost.derive_salient_points.__name__)
            if run_insights in OPTION_TRUE:
                function_list.append(JobPost.get_relevant_insights.__name__)
            if run_cover_letter in OPTION_TRUE:
                function_list.append(JobPost.generate_cover_letter.__name__)
            if run_save_pdf in OPTION_TRUE:
                function_list.append(JobPost.store_cover_letter.__name__)
            if run_generate_summary in OPTION_TRUE:
                function_list.append(JobPost.generate_summary.__name__)
            if run_customize_resume in OPTION_TRUE:
                function_list.append(JobPost.save_custom_resume.__name__)
                                                             
            self.job.runnable(function_list=function_list)
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception

    def scrape_page(self,url):
        try:
            self.page=Page(url=url)
            if self.page.response.status_code !=200:
                logging.warning('Page not found: {}'.format(self.page.response.request.url))
                return
                
            self.page.get_content()
            self.job=JobPost(file_id=None,settings=self.settings)
            self.job.parse_job_post(post_text=self.page.content,source=url)
        except (requests.exceptions.InvalidURL,requests.exceptions.HTTPError,requests.exceptions.URLRequired,requests.exceptions.MissingSchema) as e:
            print("Invalid URL")

        except Exception as e:
          logging.error('Error {} .'.format(e))
          raise Exception
     
    def refresh_user_settings(self):
        self.refresh_settings()
        if self.job!=None:
            self.job.refresh_settings()
    
    def replace_embeddings(self):
        replace_embeddings()
        combine_settings_embeddings()
    
    def check_setting_value(self,setting_name):
        try:
            display_setting_value(setting_name,self.settings.check_setting_value(setting_name=setting_name),'conversation')
            if self.job != None:
               display_setting_value(setting_name=setting_name,setting_value=self.job.settings.check_setting_value(setting_name=setting_name),context='job')
        except AttributeError as e:
            print(f'Setting [',setting_name,'] does not exist')
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception   
       
    def load_jobs_from_airtable(self):
        parse_airtable_records_for_parsing(self.settings)   
    
    def retrieve_knowledge(self):
        retrieve_knowledge_from_airtable(self.settings)
        
    def retrieve_resume_data(self,language=None):
        self.resume_data=retrieve_resume_from_airtable(self.settings,language=language)
        
    def load_anonymized_resume_into_embeddings(self):
        resume_data=self.load_resume_data()
        if resume_data is None:
            logging.warning('No resume data available')
            return
        merged_file_basename="anonymized_resume"
        merge_file(template_file_path=self.settings.anonymized_resume_template,output_file_dir=self.settings.temp_dir,output_file_basename=merged_file_basename,context=resume_data,extension='.html')
        merged_filepath=os.path.join(self.settings.temp_dir,merged_file_basename+'.html')
        embeddings_filepath=os.path.join(self.settings.resume_dir_path,self.settings.input_dir)
        convert_to_pdf(input_file_path=merged_filepath,output_file_dir=embeddings_filepath,output_file_basename=merged_file_basename,format='html',engine='pdfkit')

    def load_resume_data(self):
        if not hasattr(self,'resume_data') or self.resume_data is None:
                self.resume_data=load_resume_from_file(self.settings)
                if self.resume_data is None:
                    self.retrieve_resume_data()
       
        return self.resume_data    
    
    def display_combined_vector(self):
        combined_store_path=os.path.join(self.settings.combined_dir_path,self.settings.vector_dir)
        vector_store=VectorStore(store_path=combined_store_path,sentence_transformer=self.settings.default_sentence_transformer)
        vector_store.display()
        
    def get_relevant_insights(self,max_nb_of_points=None,skip_insighted_points=None):
        #Cast max_nb_of_points to int
        if max_nb_of_points is not None:
            max_nb_of_points=int(max_nb_of_points)
        if skip_insighted_points is not None:
            if skip_insighted_points in OPTION_TRUE:
                skip_insighted_points=True
            else:  
                skip_insighted_points=False
        self.job.get_relevant_insights(max_nb_of_points=max_nb_of_points,skip_insighted_points=skip_insighted_points)        
    
    def save_resume(self,basename=None):
        if basename is None or basename=='':
            basename=self.settings.resume_file_prefix
        save_generic_resume(output_file_dir=self.settings.generic_resume_dir,output_file_basename=basename,anonymized=False,settings=self.settings)
    
    def communicate_with_vector(self):
        communicate_with_vector_store(settings_embedding_class=CombinedEmbedding,settings=self.settings)
    
def display_setting_value(setting_name, setting_value,context):
    print(f'[bold]{context}.{setting_name}[/bold]: {setting_value}')
    

    
    
def ui(filename=None):
    try:
        conversation=Conversation()
        
        if filename is not None:
            conversation.load_job_post(filename)
        
        # Start a REPL loop
        conversation.collect_user_input()

    except Exception as e:
     logging.error(msg='Error {} .'.format(e))     
     raise Exception

if __name__ == "__main__":
    # Parse the arguments
    # parser = argparse.ArgumentParser(description='Program to interact with a job post')
    # parser.add_argument('-f','--filename', type=str, help='Basename of the existing job post history file')
    # args = parser.parse_args()     
    
    # filename=args.filename

    ui()