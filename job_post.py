from datetime import datetime
import json
import os
import logging
import uuid
from slugify import slugify


from openai import APIConnectionError

from  utils import *
from file_handler import File
from prefy import PreferencesWrapper
from parsing_templates import JobCharacteristics, RelevantInsights,CoverLetter, SalientPoint, SalientPointWithInsights,ApplicationStatus
#from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from custom_parsers import StrOutputParser
from utils import KnowledgeEmbedding,ResumeEmbedding
from langchain_core.runnables import (RunnableParallel,RunnablePassthrough)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from templating import merge_file,convert_to_pdf
from langchain.globals import set_llm_cache
from langchain.cache import InMemoryCache


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')



class History:
    # Class for storing and loading the details of a job post processing that will allow
    # to store it and retrieve it later
    def __init__(self,id, initial_job_post=None, job_characteristics=None, salient_points=None, cover_letter=None, status=None, source=None, personal_connection=None,airtable_id=None,summary=None,external_info=None):
        self.id=id
        self.source=source
        self.personal_connection=personal_connection if personal_connection != None else []
        self.external_info=external_info
        self.initial_job_post=initial_job_post
        self.job_characteristics=job_characteristics if job_characteristics!=None else JobCharacteristics()
        self.salient_points=salient_points      
        self.cover_letter=cover_letter if cover_letter!=None else CoverLetter()
        self.status =status if status!=None else ApplicationStatus()
        self.airtable_id=airtable_id
        self.summary=summary

class JobPost(PreferencesWrapper):
    def __init__(self, file_id=None,create_input_history_file=False,settings=None,initial_job_post=None,source=None,airtable_id=None):
        try:
            super(self.__class__, self).__init__(settings=settings)
            self.file_dir = self.settings.job_post_dir
            load_post=False
            #Check if file_directory exists
            if not os.path.exists(self.file_dir):
                logging.error("File directory not found: {}".format(self.file_dir))
                raise FileNotFoundError

            if file_id:
                if not create_input_history_file:               
                    load_post=True
            else:
                file_id=str(uuid.uuid4())
                
            self.history=History(file_id,initial_job_post=initial_job_post,source=source,airtable_id=airtable_id)
            self.file_name = file_id+".json"
            self.file=File(directory=self.file_dir, name=self.file_name)
            self.file.create_or_load()
            if load_post:
                self.load_job_post()
            else:
                self.update_history()
                
            if self.settings.use_airtable and self.history.airtable_id is not None:
                self.airtable_connection=AirtableConnection(settings=self.settings)

            logging.info("'{}' created/loaded.".format(self.file.filepath))

        except FileNotFoundError as e:
            logging.error("Error '{}' loading/creating job post in '{}'.".format(e,self.file_dir))
            raise FileNotFoundError
        
        except Exception as e:
            logging.error("Error {} loading/creating job post in {}.".format(e,self.file_dir))
            raise Exception

    def load_job_post(self):
        # Store what's in the history file 
        try:
            self.file.load(mode='r')
            self.file.getJSONContent()
            import_json_attributes(self.history,self.file.JSONcontent)
            if hasattr(self.history,'initial_job_post') and self.history.initial_job_post!=None and self.history.initial_job_post!=self.settings.blank_source_initial_post:
                self.history.status.has_raw_post=True
            if hasattr(self.history,'job_characteristics') and self.history.job_characteristics!=None:
                self.history.status.is_parsed=True
            if hasattr(self.history,'salient_points') and self.history.salient_points!=None:
                self.history.status.has_salient_points=True
            if hasattr(self.history,'cover_letter') and self.history.cover_letter.current_body!=None:
                self.history.status.has_cover_letter=True
            if hasattr(self.history,'summary') and self.history.summary!=None:
                self.history.status.has_custom_summary=True
                        
        except Exception as e:
            logging.error("Error {} loading/creating job post in {}.".format(e,self.file_dir))
            raise Exception   
        logging.info("Loaded job post from history file '{}'".format(self.file.filepath))
    
    def import_txt_job_post(self,source_filepath):
        try:
            with open(source_filepath,'r') as f:
                self.history.initial_job_post=f.read()
            
            self.update_history()
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
    
    def parse_job_post(self,post_text=None,source=None):

        logging.info('Starting to parse job.')

        if post_text is not None:
            self.history.initial_job_post=post_text
            
        if source is not None:
            self.history.source=source

        #Instantiate the AI model
        llm=instantiate_settings_llm("job_parse")

        #Set up a parser + inject instructions into the prompt template
        parser = JsonOutputParser(pydantic_object=JobCharacteristics)

        #Define the prompt
        prompt = PromptTemplate(  
            template=self.settings.job_parse_prompt,
            input_variables=["job_description"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        #Launch the prompt
        chain = prompt | llm | parser
        self.history.job_characteristics=extract_json_from_string(chain.invoke({"job_description":self.history.initial_job_post}))
        logging.info("Parsed job post and added to history file '{}'".format(self.file.filepath))
        self.history.status.is_parsed=True
        remove_hallucinations(self.history.job_characteristics)
        self.update_history()
        self.update_airtable_status(status=self.settings.parsed_status)       

        return self.history.job_characteristics

    def append_to_history(self,content,key):
        new_dict={key:content}
        self.file.append_to_file(new_dict)
        
    def add_personal_connection(self,text):
        # Personal conections are elements specific to the job post that are not present in the insights
        # of the job post
        self.history.personal_connection.append(text)
        self.update_history()
        
    def update_history(self):
        #Replace the content of the history file with the current job post attributes
        try:
            new_history_data=export_json_attributes(self.history)
            self.file.write_to_file(new_history_data)  
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception  

    def derive_salient_points(self):
        try:
            #Only relevant if the job post has been parsed
            if self.history.job_characteristics==None:
                if self.history.initial_job_post==None:
                    logging.warning("No job post details for parsing.")
                    raise AttributeError
                self.parse_job_post(self.history.initial_job_post)

            logging.info('Starting to derive salient points.')
            
            #Only include the relevant points of the job post
            salient_job_characteristics={
                "position":get_value_from_key("position",self.history.job_characteristics),
                "organizationdetails":get_value_from_key("organizationdetails",self.history.job_characteristics),
                "responsibilities":get_value_from_key("responsibilities",self.history.job_characteristics),
                "requirements":get_value_from_key("requirements",self.history.job_characteristics),
            }
            example_file=File(filepath=self.settings.job_classification_example)
            example_salient_points=example_file.getJSONContent()

            llm=instantiate_settings_llm("job_classification",settings=self.settings)
            parser = JsonOutputParser(pydantic_object=SalientPoint)
            prompt = PromptTemplate(  
                template=self.settings.job_classification_prompt,
                input_variables=["job_characteristics"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )
            #Launch the prompt
            chain = prompt | llm 

            response=chain.invoke({"job_characteristics":salient_job_characteristics,"example":example_salient_points})
            content=response.content
            if isinstance(content, dict) and 'points' in content:
                content= content['points']
            logging.info("Extracting JSON from: '{}'".format(content))
            salient_points=extract_json_from_string(response.content)
            self.add_salient_points_to_history( salient_points)
            logging.info("Added salient points from job post and added them to history file '{}'".format(self.file.filepath))
            self.update_airtable_status(status=self.settings.salient_point_status)       
            return self.history.salient_points

        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception

    def add_salient_points_to_history(self, salient_points):
        try:
            unsorted_salient_points = []
            for salient_point in salient_points:
                parsed_salient_point=SalientPointWithInsights.parse_obj(salient_point)
                #salient_point[self.settings.insights_rag_node]=[]
                unsorted_salient_points.append(parsed_salient_point)
                        
            try:
                self.history.salient_points=sorted(unsorted_salient_points, key=lambda x: x['importancescore'], reverse=True)
            except TypeError:
                self.history.salient_points=sorted(unsorted_salient_points, key=lambda x: x.importancescore, reverse=True)                
            finally:
                self.history.status.has_salient_points=True
                self.update_history()
                
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception

    def get_relevant_insights(self,max_nb_of_points=None,skip_insighted_points=True):
        # Only relevant if the job post has been parsed and salient points have been derived
        # Will loop through the salient points and try to find relevant experience/knowledge base to address them
        # Assumes vector base is updated

        try:
            logging.info('Starting to retrieve relevant insights for salient points.')
            if self.history.job_characteristics==None:
                if self.history.initial_job_post==None:
                    logging.warning("No job post details for parsing.")
                    raise AttributeError
                self.parse_job_post(self.history.initial_job_post)
            if self.history.salient_points==None:
                self.derive_salient_points()
            
            #Handle max_nb_of_points
            has_max=False
            if max_nb_of_points!=None and max_nb_of_points != "":
                try:
                    max_nb_of_points=int(max_nb_of_points)
                    has_max=True
                except ValueError:
                    pass
            
            #Instantiate the retrievers and check that the embeddings have been loaded
            knowledge_retriever=load_settings_retriever(KnowledgeEmbedding,number_of_documents=self.settings.insights_rag_docs)
            resume_retriever=load_settings_retriever(ResumeEmbedding,number_of_documents=self.settings.insights_rag_docs)
            
            #Instantiate the llm
            llm=instantiate_settings_llm(settings_prefix="insights_rag",settings=self.settings)

            #Retrieve the prompt
            prompt_template=self.settings.insights_rag_prompt
            insights_node_name=self.settings.insights_rag_node

            parser = JsonOutputParser(pydantic_object=RelevantInsights)
            #Loop through the salient points
            
            example_file=File(filepath=self.settings.insights_rag_example)
            example=example_file.getJSONContent()

            prompt=PromptTemplate.from_template(
                prompt_template,
                partial_variables={'example':example}
                ).partial(format_instructions=parser.get_format_instructions())
            set_llm_cache(InMemoryCache())
                    
            count_points=0
            #Loop through the salient points
            for index, salient_point in enumerate(self.history.salient_points):
                #Only the ones that haven't been insighted, unless skip_insighted_points is False
                current_insights=get_value_from_key(insights_node_name,salient_point)
                if current_insights==None or current_insights==[] or skip_insighted_points == False:
                    count_points+=1
                    if has_max and count_points>max_nb_of_points:
                        logging.info("Reached max number of insights to retrieve: {}".format(max_nb_of_points))
                        break
                    point=get_value_from_key('point',salient_point)
                    logging.info("Looking for insights for point: {}".format({point}))
                    retrieval=RunnableParallel(
                        {"resume": resume_retriever,
                        "kb": knowledge_retriever,
                        "salient_point":RunnablePassthrough() 
                        }
                    )

                    #Launch the prompt
                    chain = retrieval | prompt | llm | parser
                    try:
                        insight_list=chain.invoke(point)
                        logging.info("Raw response: {}".format(insight_list))
                        cleaned_insight_list=extract_json_from_string(insight_list)
                        insights=cleaned_insight_list['insights']
                        number_of_insights=len(insights)
                        if number_of_insights>0:
                            # Add the insights to the object's salient points
                            self.history.salient_points[index][insights_node_name]=insights
                        self.history.status.has_relevant_insights=True
                    except json.decoder.JSONDecodeError as e:
                        logging.warning("Parsing error gathering insights for point : {}".format(point))
                        continue
                    except Exception as e:
                        logging.error('Error "{}" while gathering insights for point : {}'.format(e,point))
                        continue
           # Replace history file to include added insights
            self.update_history()     
            self.update_airtable_status(status=self.settings.insighted_status)       

        except AttributeError as e:
            logging.error('Error {}. Check that your embeddings have been successfully loaded'.format(e))
            raise AttributeError
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
    
    def generate_quick_cover_letter(self):
        # Generate a cover letter based on the raw initial post
        # Requires resume and knowledge base embeddings to be loaded
        
        try:
            if self.history.initial_job_post==None:
                logging.warning("Missing job post details.")
                raise AttributeError
            logging.info('Starting to generate quick cover letter.')
            #Instantiate the combined retrievers and check that the embeddings have been loaded
            combined_retriever=load_settings_retriever(CombinedEmbedding,number_of_documents=self.settings.quick_cl_rag_docs)
            llm=instantiate_settings_llm("quick_cl",settings=self.settings)
            #Retrieve the prompt
            prompt_template=self.settings.quick_cl_prompt
            prompt=PromptTemplate.from_template(
                prompt_template
                )
            cover_letter_examples=concatenate_txt_files(self.settings.cover_letter_examples_dir,'example')
            personal_connection=contatenate_txt_xml_style(self.history.personal_connection,'relevant_info')

            document_chain=create_stuff_documents_chain(llm,prompt)
            chain=create_retrieval_chain(combined_retriever,document_chain)  
            input=self.history.initial_job_post 
            invoke_param={"input":input,"examples":cover_letter_examples,"personal_connection":personal_connection}
            cover_letter_content=chain.invoke(invoke_param)
            output_parser=StrOutputParser()
            parsed_cover_letter=output_parser.parse(cover_letter_content)
            print (parsed_cover_letter)
            updated_cover_letter_content=self.store_cover_letter(parsed_cover_letter)
            self.update_airtable_status(status=self.settings.quick_cl_status)  
            return updated_cover_letter_content
 
        except Exception as e:
            logging.error('Error {} .'.format(e))
            raise Exception

    def generate_cover_letter(self):
        # Generate a cover letter based on the parsed job characteristics, salient points, and relevant insights
        try:
            if self.history.job_characteristics==None or self.history.salient_points==None:
                logging.warning("Missing job characteristics or salient points.")
                raise AttributeError
            logging.info('Starting to generate full cover letter.')

            llm=instantiate_settings_llm("generate_cover_letter",settings=self.settings)
            #Retrieve the prompt
            prompt = PromptTemplate(  
                template=self.settings.generate_cover_letter_prompt,
                input_variables=["job_post","personal_connection", "insights","examples"],
            )
            #Launch the prompt
            chain = prompt | llm | StrOutputParser()
            job_characteristics={}
            job_characteristics['Organization']=get_value_from_key('organization',self.history.job_characteristics) 
            job_characteristics['Position']=get_value_from_key('position',self.history.job_characteristics) 
            job_characteristics['Recruiter name']=get_value_from_key('recruitername',self.history.job_characteristics) 
              
            #Retrieve cover letter examples and personal connection
            cover_letter_examples=concatenate_txt_files(self.settings.cover_letter_examples_dir,'example')
            personal_connection=contatenate_txt_xml_style(self.history.personal_connection,'relevant_info')
            
            job_post=json.dumps(job_characteristics) 
            insights=json.dumps(self.history.salient_points) 
            invoke_param={"job_post":job_post,"personal_connection":personal_connection,"insights":insights,"examples":cover_letter_examples}
            cover_letter_content=chain.invoke(input=invoke_param)
            print (cover_letter_content)
            updated_cover_letter_content=self.store_cover_letter(cover_letter_content)
            self.history.status.has_full_cover_letter=True 
            self.update_airtable_status(status=self.settings.full_cl_status)            
            return updated_cover_letter_content

        except APIConnectionError as e:
            logging.error('Failed connection to {}'.format(e.request.url.host))
            raise APIConnectionError
        except Exception as e:
            logging.error('Error {} .'.format(e))
            raise Exception

    def store_cover_letter(self, ai_cover_letter):
        self.history.cover_letter.current_body=ai_cover_letter
        self.history.status.has_cover_letter=True
        self.update_history()
        return  self.history.cover_letter.current_body

    def store_summary(self, summary):
        self.history.summary=summary
        self.history.status.has_custom_summary=True
        self.update_history()
        return  self.history.summary
     
    def store_cover_letter_as_example(self):
        # Stores the content of the cover letter as an example for future cover letter generation
        try:
            if not self.history.status.has_cover_letter:
                logging.warning("Missing cover letter content.")
                raise AttributeError
            
            file_path=os.path.join(self.settings.cover_letter_examples_dir,os.path.basename(self.history.cover_letter.file_name)+'.txt')
            with open(file_path, 'w') as file:
                # Write the content of the variable to the file
                file.write(self.history.cover_letter.current_body)
            logging.info("Stored cover letter as example: {}".format(file_path))
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
       
    def create_or_load_application_directory(self):
        try:
            if not hasattr(self.history.cover_letter, "application_directory") or self.history.cover_letter.application_directory==None:           
                root_application_dir=self.settings.root_application_dir_path
                path_dir_list=[]
                file_name_list=[self.settings.cover_letter_file_prefix]
                if not get_value_from_key('job_characteristics',self.history) is None:
                    if not get_value_from_key('organization',self.history.job_characteristics) is None:
                        path_dir_list.append(get_value_from_key('organization',self.history.job_characteristics))
                        file_name_list.append(get_value_from_key('organization',self.history.job_characteristics))
                    if not get_value_from_key(key='position',object=self.history.job_characteristics) is None:
                        path_dir_list.append(get_value_from_key(key='position',object=self.history.job_characteristics))
                        file_name_list.append(get_value_from_key(key='position',object=self.history.job_characteristics))
                elif get_value_from_key(key='id',object=self.history) is not None:
                    path_dir_list.append(get_value_from_key(key='id',object=self.history))
                else:
                    logging.warning("Missing job post details.")
                    raise AttributeError
                file_name_list.append(self.settings.cover_letter_file_suffix)
                self.history.cover_letter.directory=os.path.join(root_application_dir,*path_dir_list)
            os.makedirs(self.history.cover_letter.directory,exist_ok=True)
            self.history.cover_letter.file_name=slugify(str.join('_',file_name_list))
            self.update_history()
            return self.history.cover_letter.directory
            
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
    
    def save_cover_letter(self):
        try:
            logging.info('Starting to save cover letter.')
            current_date = datetime.now()

            if self.history.cover_letter.current_body==None:   
                logging.warning("Missing cover letter.")
                raise AttributeError

            output_directory=self.create_or_load_application_directory()
            contact=load_resume_from_file()
            context={
                'organization':self.history.job_characteristics.organization,
                'position':self.history.job_characteristics.position,
                'date':current_date.strftime("%B %d, %Y"),
                'cover_letter_body': self.history.cover_letter.current_body
            }
            context.update(contact)
            self.history.cover_letter.merged_file=merge_file(self.settings.cover_letter_template_path,self.settings.root_application_temp_path,self.history.cover_letter.file_name,context)
            self.history.cover_letter.final_file=convert_to_pdf(self.history.cover_letter.merged_file.filepath,output_directory,self.history.cover_letter.file_name,format='html',engine='pdfkit')
            self.update_airtable_status(status=self.settings.printed_cl_status)             
        
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception
     
    def save_custom_resume(self,template_file_path=None):
        try:
            logging.info('Starting to save resume.')
            current_date = datetime.now()

            if self.history.summary==None:   
                logging.info('Using generic summary.')
            else:
                logging.info('Using custom summary.')                

            if template_file_path is None:
                template_file_path=getattr(self.settings,self.settings.default_resume)
            temp_dir=self.settings.temp_dir
            output_directory=self.create_or_load_application_directory()
            context=load_resume_from_file()
            if hasattr(self.history,'summary') and self.history.summary is not None:
                context['contact']['summary']=self.history.summary
            if self.history.status.is_parsed:
                context['initial_job_post']=get_value_from_key("responsibilities",self.history.job_characteristics)+get_value_from_key("requirements",self.history.job_characteristics)
            else:
                if self.history.status.has_raw_post:
                    context['initial_job_post']=self.history.initial_job_post
            custom_html_resume=merge_file(template_file_path=template_file_path,output_file_dir=temp_dir,output_file_basename=self.settings.resume_file_prefix,context=context,extension='.html')
            return convert_to_pdf(input_file_path=custom_html_resume.filepath,output_file_dir=output_directory,output_file_basename=self.settings.resume_file_prefix,format='html',engine='pdfkit')
        except Exception as e:
         logging.error('Error {} .'.format(e))
         raise Exception         
     
    def runnable(self,function_list):
        # Runs a list of functions in the order of the list
         try:
            for function in function_list:
                getattr(self,function)()
         except Exception as e:
            logging.error('Error {} .'.format(e))
            raise Exception
        
    def update_airtable_status(self,status):
        if hasattr(self,"airtable_connection") and self.airtable_connection is not None:
            self.airtable_connection.update_job_status(self.history.airtable_id,status)
            
    def generate_summary(self):
    # Generate an executive summary based on the raw initial post
    # Requires resume and knowledge base embeddings to be loaded
    
        try:
            if self.history.initial_job_post==None:
                logging.warning("Missing job post details.")
                raise AttributeError
            logging.info('Starting to generate summary.')
            #Instantiate the combined retrievers and check that the embeddings have been loaded
            combined_retriever=load_settings_retriever(CombinedEmbedding,number_of_documents=self.settings.summary_rag_docs)
            llm=instantiate_settings_llm("generate_summary",settings=self.settings)
            #Retrieve the prompt
            prompt_template=self.settings.generate_summary_prompt
            prompt=PromptTemplate.from_template(
                prompt_template,
                )
            summary_examples=concatenate_txt_files(self.settings.summary_example_dir,'example')
            document_chain=create_stuff_documents_chain(llm,prompt)
            chain=create_retrieval_chain(combined_retriever,document_chain)  
            job_post=self.history.initial_job_post 
            invoke_param={"input":job_post,"examples":summary_examples,"context":combined_retriever}
            summary=chain.invoke(invoke_param)
            output_parser=StrOutputParser()
            parsed_summary=output_parser.parse(summary['answer'])
            print (parsed_summary)
            self.history.status.has_custom_summary=True
            updated_summary=self.store_summary(parsed_summary)
            return updated_summary
 
        except Exception as e:
            logging.error('Error {} .'.format(e))
            raise Exception
    def refresh_history_from_file(self):
        self.history=History(id=self.history.id)
        self.load_job_post()
def create_job_from_file(filepath, source=None):
    try:
        with open(filepath,'r') as f:
            initial_job_post=f.read()
        basename=os.path.splitext(os.path.basename(filepath))[0]
        
        new_job=JobPost(file_id=basename,initial_job_post=initial_job_post,source=source,create_input_history_file=True)
        return new_job
    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception         
   
