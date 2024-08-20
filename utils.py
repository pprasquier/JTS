import os
import logging
import json
from typing import Any, Dict, List, Optional
import requests
import re

from airtablehelper import AirtableConnection
import parsing_templates as pt
from templating import *

from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.memory import ConversationBufferMemory
from scraper import Page
from prefy import Preferences
from file_handler import Embedding, VectorStore, File


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')

def instantiate_settings_llm(settings_prefix,settings=None):
    #Instantiate the AI model using settings starting with a specific prefix
    try:
        if settings==None:
            settings=Preferences('settings_files')

        model_name=getattr(settings,settings_prefix+"_model_name")
        base_url=getattr(settings,settings_prefix+"_base_url")
        temperature=getattr(settings,settings_prefix+"_temperature")
        max_tokens=getattr(settings,settings_prefix+"_tokens")
        timeout=getattr(settings,settings_prefix+"_timeout")

        llm = instantiate_llm(model_name, base_url, temperature, max_tokens,timeout=timeout,llm_api=settings.llm_api)
        return llm
    except AttributeError as e:
        logging.error("Unknown attribute with prefix '{}'.".format(e,settings_prefix))
        raise AttributeError
    except Exception as e:
        logging.error("Error '{}' instantiating settings_llm with prefix '{}'.".format(e,settings_prefix))
        raise Exception

def instantiate_llm(model_name, base_url, temperature, max_tokens,timeout,llm_api='ChatOpenAI'):
    match llm_api:
        case "ChatOpenAI":
            llm = ChatOpenAI(
                temperature=temperature,
                max_tokens=max_tokens,
                model=model_name,
                base_url=base_url,
                timeout=timeout
                )
            return llm
        case "Ollama":
            llm = Ollama(
                temperature=temperature,
                # max_tokens=max_tokens,
                model=model_name,
                base_url=base_url,
                timeout=timeout
                )
            return llm
        case _:
            logging.error("Unknown llm_api '{}'.".format(llm_api))
            raise Exception

class SettingsEmbedding(Embedding):
    #Derives an embedding's characteristics from the settings files
    def __init__(self,prefix,**kwargs):
        from prefy import Preferences

        settings=Preferences('settings_files')
        root_dir=getattr(settings,prefix+"_dir_path")
        new_dir_name=getattr(settings,"input_dir")
        vector_dir_name=getattr(settings,"vector_dir")
        processed_dir_name=getattr(settings,"processed_dir")
        sentence_transformer=getattr(settings,prefix+"_sentence_transformer")
        doc_type=getattr(settings,prefix+"_doc_type")
        super(SettingsEmbedding, self).__init__(
            root_dir=root_dir,
            new_dir_name=new_dir_name,
            vector_dir_name=vector_dir_name,
            processed_dir_name=processed_dir_name,
            doc_type=doc_type,
            sentence_transformer=sentence_transformer,
            **kwargs
        )
class CombinedEmbedding(SettingsEmbedding):
    def __init__(self):
        super(CombinedEmbedding,self).__init__("combined")
        
class ResumeEmbedding(SettingsEmbedding):
    def __init__(self):
        super(ResumeEmbedding,self).__init__("resume")

class KnowledgeEmbedding(SettingsEmbedding):
    def __init__(self):
        csv_args={"delimiter": ",", "quotechar": '"', "fieldnames": ["Question", "Answer"]}
        super(KnowledgeEmbedding,self).__init__("knowledge",csv_args=csv_args)

def replace_embeddings():
    #Clears current embeddings and replaces them with what's currently in the input directories
    try:
        knowledge=KnowledgeEmbedding()
        knowledge.build_index(mode='replace')
        resume=ResumeEmbedding()
        resume.build_index(mode='replace')
        combine_settings_embeddings()

    except Exception as e:
        logging.error('Error: {}'.format(e))

def combine_settings_embeddings():
        knowledge=KnowledgeEmbedding()
        knowledge.load_index()
        resume=ResumeEmbedding()
        resume.load_index()
        vectorstore_list=[knowledge.store.db,resume.store.db]
        combined=CombinedEmbedding()
        combined.merge_and_save_vectorbases(vectorstore_list)

class JSONObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

def import_json_attributes(obj, data):
    #Add attributes to an object from a JSON dictionary
    for key, value in data.items():
        if isinstance(value, dict):
            setattr(obj, key, JSONObject(**value))
        else:
            setattr(obj, key, value)
            
def export_json_attributes(obj):
    #Export attributes of an object to a JSON dictionary
    try:
        data = {}
        for key, value in vars(obj).items():
            if isinstance(value,(str, int, float, bool, dict, type(None))):
                data[key] = value
            elif isinstance(value,list):
                    if len(value)==0 or isinstance(value[0], (str, int, float, bool, dict, type(None))):
                        data[key] = value
                    else:
                        data[key] = [export_json_attributes(item) for item in value]
                        
            else: #if isinstance(value, (JSONObject,pt.SalientPointWithInsights,pt.CoverLetter)):
                data[key] = export_json_attributes(value)
            
        return data
    except Exception as e:
     logging.error('Error {} .'.format(e))
     raise Exception

def concatenate_txt_files(directory,separator):
    try:
        files_content = []
        found_files = False
        
        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                file_path = os.path.join(directory, filename)
                with open(file_path, 'r') as file:
                    found_files = True
                    file_content = file.read()
                    files_content.append(file_content)
        if not found_files:
            logging.warning('No .txt files found in {}.'.format(directory))
            raise FileNotFoundError  
        concatenated_content=contatenate_txt_xml_style(files_content,separator)
                  
        return concatenated_content   
    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception

def contatenate_txt_xml_style(text_list,separator):
    try:
        concatenated_content = ""
        text_iterator = 1
        found_text = False
       
        for text in text_list:
            found_text = True
            concatenated_content += f"<{separator}{text_iterator}>\n{text}\n</{separator}{text_iterator}>\n\n"
            text_iterator += 1
        if not found_text:
            logging.warning('No text in input list.')
            return None
                  
        return concatenated_content   
    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception
   
   
def load_settings_retriever(embeddingClass,number_of_documents=4):
    # Loads a retriever from a pre-defined embedding
    try:
        embedding=embeddingClass()
        embedding.load_index()
        if embedding.store.doc_count==0:
            logging.warning("No document found in {}'s index.".format(embeddingClass.__name__))
            raise AttributeError
        retriever = embedding.store.db.as_retriever(search_kwargs={'k': number_of_documents})
        return retriever            
    except Exception as e:
        logging.error('Error {} .'.format(e))
        raise Exception   
        
def extract_json_from_string(input_string):
    if input_string is None:
        return None
    # Check if the input is a JSON string
    if isinstance(input_string, str):
        try:
            json_object = json.loads(input_string)
            return json_object
        except json.JSONDecodeError:
            pass
        
    # Check if the input is a dictionary or list
    if isinstance(input_string, (dict, list)):
        return input_string
    
    # Function to replace single quotes with double quotes while preserving single quotes inside values
    def preprocess_string(s):
        # Regular expression to match keys and string values in single quotes
        pattern = re.compile(r"(?<!\\)'(.*?)'(?=\s*[:,}\]])")
        return pattern.sub(r'"\1"', s)

    # Preprocess the input string to replace single quotes with double quotes
    input_string = preprocess_string(input_string)

    # Function to find the first complete JSON object or array
    def find_complete_json(s):
        brackets = {'{': '}', '[': ']'}
        stack = []
        start = None

        for i, char in enumerate(s):
            if char in brackets:
                if start is None:
                    start = i
                stack.append(brackets[char])
            elif char in brackets.values():
                if stack and char == stack[-1]:
                    stack.pop()
                    if not stack:
                        return s[start:i+1]
                elif not stack:
                    return None

        return None

    # Find the first complete JSON part in the input string
    json_string = find_complete_json(input_string)
    
    if json_string:
        try:
            json_object = json.loads(json_string)
            return json_object
        except json.JSONDecodeError:
            return None

    return None

def communicate_with_vector_store(settings_embedding_class=None,embedding_model_name=None,parent_directory_path=None,settings=None):
    if settings==None:
        settings=Preferences('settings_files')
    if settings_embedding_class==None: 
        if parent_directory_path==None:
            parent_directory_path="test_data\\Embeddings\\resume_pdf"

        store_path=os.path.join(parent_directory_path, settings.vector_dir)
        store=VectorStore(store_path=store_path,sentence_transformer=embedding_model_name)
        store.display()
        retriever = store.db.as_retriever()
    else:
        retriever=load_settings_retriever(settings_embedding_class)

    llm = instantiate_settings_llm("vector_communication")

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    memory.load_memory_variables({})
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        memory=memory,
        retriever=retriever
    )
    # Start a REPL loop
     
    while True:
        user_input = input("Ask a question. Type 'exit' to quit.\n>")
        if user_input=="exit":
            break
        memory.chat_memory.add_user_message(user_input)
        result = qa_chain({"question": user_input})
        response = result["answer"]
        memory.chat_memory.add_ai_message(response)
        print("AI:", response)

def parse_airtable_records_for_parsing(settings=None) -> list:
    from job_post import JobPost

    try:        
        records_imported=[]
        if settings is None:
            settings=Preferences('settings_files')
        
        airtable_connection=AirtableConnection(settings)
        if airtable_connection is None:
            return 0
        
        jobs=airtable_connection.job.get_all_records(view_id=settings.parsing_view_id)
        for job in jobs:
            airtable_id=job['id']
            this_job=job['fields']
            source = get_value_from_key(settings.source_field_name, this_job)
            job_description=get_value_from_key(settings.job_description_field_name, this_job)
            
            # If only the source is provided, try to parse it
            if job_description is None:
                try:
                    parse_page=Page(url=source)
                    job_description=parse_page.get_content()
                except (requests.exceptions.InvalidURL,requests.exceptions.HTTPError,requests.exceptions.URLRequired,requests.exceptions.MissingSchema) as e:
                    logging.warning('Unable to scrape: {}'.format(source))

            jts_job=JobPost(create_input_history_file=True,source=source,initial_job_post=job_description,airtable_id=airtable_id)
            records_imported.append(jts_job)
            airtable_connection.update_job_post(airtable_id,**{settings.jts_id_field_name:jts_job.history.id})
            airtable_connection.update_job_status(airtable_id,settings.imported_status)            
            if job_description is not  None:
                jts_job.parse_job_post()                
        logging.info('Imported {} records.'.format(len(records_imported)))    
        return records_imported    
    
    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception

def get_value_from_key(key, object,translation_list=None,record_id=None,settings=None):
    # This function returns the value of a key in an object, or None if the key is not found
    try:
        if translation_list is not None and record_id is not None:
                translated_value=find_first_match_in_translation_list(collection=translation_list,field_name=key,record_id=record_id,settings=settings)
                if translated_value is not None:
                    return translated_value        
        if(isinstance(object,dict)):
            value=object[key]
        else:
            value=getattr(object,key)
        return value

    except (KeyError,AttributeError) as e:
        return None
    except Exception as e:
        logging.error('Error {} .'.format(e))
        raise Exception

def find_first_match_in_translation_list(collection,field_name, record_id,settings):
    for record in collection:
        item=record['fields']
        if get_value_from_key(key=settings.translation_field_field_name,object=item)==field_name:
            if record_id in get_value_from_key(key=settings.translation_linked_record_field_name,object=item):
                return get_value_from_key(key=settings.translation_translation_field_name,object=item)
    return None
    
def retrieve_resume_from_airtable(settings=None,language=None):
    #  Retrieves resume data from Airtable and stores it into a JSON file
    # If a language is provided, the corresponding translations will be retrieved and substituted in the resume
    try:
        if settings is None:
            settings=Preferences('settings_files')
        if not settings.use_airtable_resume:
            logging.warning('Airtable is not set up to store resumes.')
            return            
        at=AirtableConnection(settings)
        if at is None:
            logging.warning('Unable to connect to Airtable.')
            return
        
        if language is not None:
            at_translations=at.translations.get_records_by_match(match_conditions={settings.translation_language_field_name:language})
        else:
            at_translations = None
        individual_record_id = settings.airtable_individual_id
        if individual_record_id is None:
            logging.warning('Individual id is not defined [airtable_individual_id].')
            return                  
        
        resume=pt.Resume(languages=[],certifications=[],experiences=[])
        
        # Get the individual record from Airtable
        at_contact=at.individual.get_record_by_id(individual_record_id)
        at_individual=at_contact['fields']
        resume.contact=pt.Contact(
            full_name=get_value_from_key(settings.individual_full_name_field_name, object=at_individual),
            email=get_value_from_key(settings.individual_email_field_name, at_individual,translation_list=at_translations,record_id=individual_record_id,settings=settings),
            phone=get_value_from_key(settings.individual_phone_field_name,at_individual,translation_list=at_translations,record_id=individual_record_id,settings=settings),
            location=get_value_from_key(key=settings.individual_location_field_name, object=at_individual,translation_list=at_translations,record_id=individual_record_id,settings=settings),
            summary=get_value_from_key(key=settings.individual_summary_field_name,object=at_individual,translation_list=at_translations,record_id=individual_record_id,settings=settings)
        )
        logging.info('Retrieving resume data for {}.'.format(resume.contact.full_name))
        
        linked_to_individual={settings.individual_id_field_name:individual_record_id}

        # Get experiences from Airtable
        at_experiences=at.experiences.get_records_by_match(match_conditions=linked_to_individual,sort_fields=[f"{settings.experience_order_field_name}"])
        for at_experience in at_experiences:
            experience_id=at_experience['id']
            at_skills=at.skills.get_records_by_search(searched_value=experience_id,within_field_name=settings.experience_id_field_name)
            skills = [item['fields'][settings.skill_name_field_name] for item in at_skills]
            at_tasks=at.tasks.get_records_by_match({settings.experience_id_field_name:experience_id})
            tasks = [item['fields'][settings.task_description_field_name] for item in at_tasks]
            at_experience_content=at_experience['fields']
            resume.experiences.append(pt.Experience(
                organization=get_value_from_key(object=at_experience_content,key=settings.experience_organization_field_name),
                type=get_value_from_key(object=at_experience_content,key=settings.experience_type_field_name),
                url=get_value_from_key(object=at_experience_content,key=settings.experience_organization_field_name),
                start_year=get_value_from_key(object=at_experience_content,key=settings.experience_startyear_field_name),
                end_year=get_value_from_key(object=at_experience_content,key=settings.experience_end_year_field_name),
                start_month=get_value_from_key(object=at_experience_content,key=settings.experience_startmonth_field_name),
                end_month=get_value_from_key(object=at_experience_content,key=settings.experience_end_month_field_name),
                location=get_value_from_key(object=at_experience_content,key=settings.experience_location_field_name),
                position=get_value_from_key(object=at_experience_content,key=settings.experience_position_field_name),
                organization_details=get_value_from_key(object=at_experience_content,key=settings.experience_organizationdetails_field_name),
                skills=skills,
                responsibilities=tasks
                ))

        logging.info('Retrieved {} experiences.'.format(len(at_experiences)))    

        # Get languages from Airtable
        at_languages=at.languages.get_records_by_match(match_conditions=linked_to_individual)
        for at_language in at_languages:
            at_language_content=at_language['fields']
            resume.languages.append(pt.Language(
                language=get_value_from_key(object=at_language_content,key=settings.language_name_field_name),
                proficiency=get_value_from_key(object=at_language_content,key=settings.language_proficiency_field_name)))
        logging.info('Retrieved {} languages.'.format(len(at_languages)))       

        # Get certfications from Airtable
        at_certifications=at.certifications.get_records_by_match(match_conditions=linked_to_individual)
        for at_certification in at_certifications:
            at_certification_content=at_certification['fields']
            resume.certifications.append(pt.Certification(
                issuer=get_value_from_key(object=at_certification_content,key=settings.certification_issuer_field_name),
                certification=get_value_from_key(object=at_certification_content,key=settings.certification_name_field_name)))
        logging.info('Retrieved {} certifications.'.format(len(at_certifications)))    
        
        resume_data=export_json_attributes(resume)
        with open(settings.resume_data_filepath, 'w') as file:
            json.dump(resume_data, file, indent=4)
        logging.info('Saved resume data to {}'.format(settings.resume_data_filepath))
        return resume_data
    
    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception
    
def retrieve_knowledge_from_airtable(settings=None):
   #  Retrieves knowledge data from Airtable and stores it into Embeddings directory as a csv file
    try:
        import csv
        if settings is None:
            settings=Preferences('settings_files')
        if not settings.use_airtable_resume:
            logging.warning('Airtable is not set up to store resumes.')
            return  
        individual_record_id = settings.airtable_individual_id
        if individual_record_id is None:
            logging.warning('Individual id is not defined [airtable_individual_id].')
            return             
        at=AirtableConnection(settings)
        if at is None:
            logging.warning('Unable to connect to Airtable.')
            return
       
        # Get the individual record from Airtable      
        linked_to_individual={settings.individual_id_field_name:individual_record_id}
        view_id=settings.knowledge_view_id

        # Get experiences from Airtable
        at_knowledge=at.knowledge.get_records_by_match(match_conditions=linked_to_individual,view_id=view_id)
        fieldnames=[settings.knowledge_question_field_name,settings.knowledge_answer_field_name]
        filepath=os.path.join(settings.knowledge_dir_path,settings.input_dir,'knowledge.csv')
        # Extract data with specific fields
        filtered_data = []
        for record in at_knowledge:
            filtered_record = {field: record['fields'].get(field, '') for field in fieldnames}
            filtered_data.append(filtered_record)
        with open(filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames,quotechar='"', quoting=csv.QUOTE_ALL)
            
            # Write the header
            writer.writeheader()
            
            # Write the data rows
            for row in filtered_data:
                writer.writerow(row)

        logging.info('Saved knowledge to {}'.format(filepath))

    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception      

def load_resume_from_file(settings=None):
    try:
        if settings is None:
            settings=Preferences('settings_files')
        context_file=File(os.path.dirname(settings.resume_data_filepath),os.path.basename(settings.resume_data_filepath))
        if context_file is not None:    
            return context_file.getJSONContent()
        else:
            logging.warning('Unable to load resume data from {}'.format(settings.resume_data_filepath))
            return None

    except Exception as e:
       logging.error('Error {} .'.format(e))
       raise Exception      

def save_generic_resume(output_file_dir,output_file_basename,anonymized=None,settings=None):
    if settings is None:
        settings=Preferences('settings_files')
    context_file=File(filepath=settings.resume_data_filepath)
    context=context_file.getJSONContent()
    if anonymized:
        template_file_path=settings.anonymized_resume_template
    else:
        template_file_path=settings.resume_template
    merged_file=merge_file(template_file_path=template_file_path,output_file_dir=settings.temp_dir,output_file_basename=output_file_basename,context=context,extension='.html')
    resume_file=convert_to_pdf(input_file_path=merged_file.filepath,output_file_dir=output_file_dir,output_file_basename=output_file_basename,format='html',engine='pdfkit')
    return resume_file

def remove_hallucinations(object):
    #Clear attributes containing obvious hallucinations from an object
    PROHIBITED_TERMS = ["John Doe", "johndoe", "ACME", "example.com"]
    if isinstance(object, dict):
        for key, value in object.items():
            if isinstance(value, str) and any(term in value for term in PROHIBITED_TERMS):
                object[key] = None
                logging.info('Removed {} from {}.'.format(value,key))
    else:
        for attr, value in object.__dict__.items():
            if isinstance(value, str) and any(term in value for term in PROHIBITED_TERMS):
                setattr(object, attr, None)
                logging.info('Removed {} from {}.'.format(value,attr))

if __name__ == "__main__":
    settings=Preferences('settings_files')
    ''' TEST LOADING SETTINGS EMBEDDINGS    
        retriever=load_settings_retriever(KnowledgeEmbedding)
        print(retriever) 
    '''
    #retrieve_knowledge_from_airtable(individual_record_id='rechMyPhcxWzsuTQ9')
     #retrieve_resume_from_airtable(language='Portuguese')
    concatenated_text=concatenate_txt_files(settings.cover_letter_examples_dir,"cover")
    print(concatenated_text)
""" TEST COMMUNICATING WITH CUSTOM VECTOR STORE
    settings=Settings('settings_files')
    #prefix='resume' 
    prefix='knowledge'
    #root_dir=getattr(settings,"resume_dir_path")
    root_dir=getattr(settings,prefix+"_dir_path")
    embedding_model_name=getattr(settings,prefix+"_sentence_transformer")
    communicate_with_vector_store(embedding_model_name=embedding_model_name,parent_directory_path=root_dir)  """
    
    
    
