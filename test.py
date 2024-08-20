import unittest
import tempfile
import os
import json
import logging
import shutil

import requests

from utils import *
from file_handler import File, Embedding
from prefy import Preferences
from job_post import *
from airtablehelper import *
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from templating import *

EMBEDDING_MODEL="all-mpnet-base-v2"
EXAMPLE_FILES_DIR = "example_files"
TEST_DATA_DIR='test_data'
SETTINGS_DIR='settings_files'
EXAMPLE_JOB_POST_PATH='example_files\\job_post.txt'
os.makedirs(TEST_DATA_DIR, exist_ok=True)

  # Define the Document class for demonstration purposes
class Vector:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

class TestSettings(unittest.TestCase):
    def test_auto_settings(self):
    # Create temporary directory and JSON files
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create JSON files
            json_file1 = os.path.join(tmpdirname, "settings1.json")
            json_file2 = os.path.join(tmpdirname, "settings2.json")
            with open(json_file1, "w") as file:
                json.dump([
                    {"type": "Settings", "key": "deactivate_setting_file", "value": False},
                    {"type": "Embeddings", "key": "resume_dir_path", "value": "/path1"},
                    {"type": "Embeddings", "key": "insight_dir_path", "value": "/path1"},
                ], file)
            with open(json_file2, "w") as file:
                json.dump([
                    {"type": "Settings", "key": "deactivate_setting_file", "value": True},
                    {"type": "Embeddings", "key": "resume_dir_path", "value": "/path2"}
                ], file)
            with open(json_file2, "w") as file:
                json.dump([
                    {"type": "Settings", "key": "deactivate_setting_file", "value": False},
                    {"type": "Embeddings", "key": "insight_dir_path", "value": "/path3"}
                ], file)

            # Call the function
            result = Preferences(tmpdirname)

            # Verify the result
            self.assertEqual(result.insight_dir_path, "/path3")
            self.assertEqual(result.resume_dir_path,"/path1")

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.settings=Preferences(SETTINGS_DIR)
    def test_instantiate_settings_llm(self):
        successful_llm = instantiate_settings_llm("job_parse")
        self.assertIsInstance(successful_llm, (ChatOpenAI,Ollama))
        with self.assertRaises(AttributeError): 
            instantiate_settings_llm("not_a_llm")

    def test_extract_json_from_valid_json_string(self):
        input_string = '{"key": "value"}'
        expected_json = {"key": "value"}
        self.assertEqual(extract_json_from_string(input_string), expected_json)

    def test_extract_json_from_invalid_json_string(self):
        input_string = "This is some text. Here is a JSON object: {'key': 'value'. More text."
        self.assertIsNone(extract_json_from_string(input_string))

    def test_extract_json_from_string_with_json_inside(self):
        input_string = 'This is some text. Here is a JSON object: {"another_key": "another_value"}'
        expected_json = {"another_key": "another_value"}
        self.assertEqual(extract_json_from_string(input_string), expected_json)

    def test_extract_json_from_empty_string(self):
        input_string = ""
        self.assertIsNone(extract_json_from_string(input_string))

    def test_extract_json_from_non_string_input(self):
        input_string = None
        self.assertIsNone(extract_json_from_string(input_string))

    def test_extract_json_from_json_list(self):
        input_string = '[{"key1": "value1"}, {"key2": "value2"}]'
        expected_json = [{"key1": "value1"}, {"key2": "value2"}]
        self.assertEqual(extract_json_from_string(input_string), expected_json)

    def test_concatenate_with_files(self):
        directory = self.settings.cover_letter_examples_dir
        separator = 'example'
        concatenated_text=concatenate_txt_files(directory,separator)        
        self.assertIn("<example1>", concatenated_text)
        self.assertIn("</example1>", concatenated_text)

        
class TestFileHandler(unittest.TestCase):
    def setUp(self):
        # Create a directory for testing
        self.test_dir = TEST_DATA_DIR
        os.makedirs(self.test_dir, exist_ok=True)
        self.example_files_dir = EXAMPLE_FILES_DIR 
        self.example_resume_json_file = os.path.join(self.example_files_dir,'resume.json')
        self.example_insights_csv_file = os.path.join(self.example_files_dir,'knowledge.csv')
        self.example_resume_pdf_file = os.path.join(self.example_files_dir,'CV_PP.pdf')
        self.embeddings_dir=os.path.join(self.test_dir, "Embeddings")
        self.embeddings_resume_dir=os.path.join(self.embeddings_dir, "resume")
        self.embeddings_resume_new_dir=os.path.join(self.embeddings_resume_dir, "new")
        self.embeddings_resume_new_file=os.path.join(self.embeddings_resume_new_dir,"resume.json")
        self.embeddings_resume_pdf_dir=os.path.join(self.embeddings_dir, "resume_pdf")
        self.embeddings_resume_pdf_new_dir=os.path.join(self.embeddings_resume_pdf_dir, "new")
        self.embeddings_resume_pdf_new_file=os.path.join(self.embeddings_resume_pdf_new_dir,"resume.pdf")
        self.embeddings_knowledge_dir=os.path.join(self.embeddings_dir, "knowledge")
        self.embeddings_knowledge_new_dir=os.path.join(self.embeddings_knowledge_dir, "new")
        self.embeddings_knowledge_new_file=os.path.join(self.embeddings_knowledge_new_dir,"knowledge.csv")
        self.embeddings_model_name = "all-mpnet-base-v2"
        self.embeddings_model = SentenceTransformerEmbeddings(model_name=self.embeddings_model_name)
        self.append_json_file = os.path.join(self.test_dir, 'example.json')
        self.append_csv_file = os.path.join(self.test_dir, 'example.csv')
        self.append_pdf_file = os.path.join(self.test_dir, 'example.pdf')
        self.append_txt_file = os.path.join(self.test_dir, 'example.txt')
        self.append_md_file = os.path.join(self.test_dir, 'example.md')
        self.append_data = {'key1': 'value1', 'key2': 'value2'}
    def test_assert_resume_json_present(self):
        # Check if resume.json file is present in the example_files directory
        self.assertTrue(os.path.exists(self.example_resume_json_file))
    
    
    def test_load_existing_json_file(self):
        # Create a test JSON file
        test_data = {'key': 'value'}
        with open(os.path.join(self.test_dir, 'test_file.json'), 'w') as f:
            json.dump(test_data, f)

        # Create FileHandler instance and load the file
        file_handler = File(directory=self.test_dir, name='test_file.json')
        loaded_data = file_handler.getJSONContent()


        self.assertEqual(loaded_data, test_data)
        file_handler.file.close()

    def test_load_non_existing_file(self):
        # Create FileHandler instance for non-existing file
        file_handler = File(directory=self.test_dir, name='non_existing_file.json')
        with self.assertRaises(FileNotFoundError):
            file_handler.load('r')

    def test_load_invalid_json_file(self):
        # Create an invalid JSON file
        with open(os.path.join(self.test_dir, 'invalid_json_file.json'), 'w') as f:
            f.write("this is not a valid JSON")

        # Create FileHandler instance and try to load the invalid JSON file
        file_handler = File(directory=self.test_dir, name='invalid_json_file.json')
        loaded_data = file_handler.load('r')

        self.assertIsNone(loaded_data)
        file_handler.file.close()

    def test_create_or_load_existing_file(self):
        # Create a test JSON file
        test_data = {'key': 'value'}
        with open(os.path.join(self.test_dir, 'existing_file.json'), 'w') as f:
            json.dump(test_data, f)

        # Create FileHandler instance and try to load the existing file
        file_handler = File(directory=self.test_dir, name='existing_file.json')
        loaded_data=file_handler.getJSONContent()

        self.assertEqual(loaded_data, test_data)
        file_handler.file.close()

    def test_write_to_file(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')
        # Create a test JSON file

        try:
            file_handler = File(directory=self.test_dir, name='existing_file.json')
            file_handler.create_or_load()
            test_data = {'key': 'value'}
            file_handler.write_to_file(test_data)

            # Check content of written data
            verif_file=File(directory=self.test_dir, name='existing_file.json')
            verif_file.load()
            loaded_data=verif_file.getJSONContent()
            file_handler.file.close()       
            self.assertEqual(loaded_data, test_data)

        except Exception as e:
            logging.error("Error '{}' writing to file '{}'.".format(e,file_handler.name))

    def test_embedding_build_no_file(self):
        noDocxDirectory=Embedding(root_dir=self.test_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name="vector", doc_type="csv",sentence_transformer=self.embeddings_model_name)   
        os.makedirs(noDocxDirectory.new_directory, exist_ok=True)
        noDocxDirectory.build_index()
        self.assertEqual(noDocxDirectory.new_files_count,0)  

    def test_embedding_build_json_file(self):
        jsonDirectory=Embedding(root_dir=self.test_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name="vector", doc_type="json",sentence_transformer=self.embeddings_model_name)   
        os.makedirs(jsonDirectory.new_directory, exist_ok=True)
        test_data = {'key': 'value'}
        with open(os.path.join(jsonDirectory.new_directory, 'vectorizing_file.json'), 'w') as f:
            json.dump(test_data, f)

        jsonDirectory.build_index()
        # TBC - Update to check whether the file has been created
        self.assertEqual(jsonDirectory.new_files_count,1)  

    def test_embedding_unknown_model(self):
     with self.assertRaises(OSError):
        wrong_model=Embedding(root_dir=self.embeddings_resume_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name="vector", doc_type="json",sentence_transformer="unknown_model")

    def test_embedding_one_json_file(self):
        # Copy the resume.json file to the test_data/new directory and build its index
        if os.path.exists(self.embeddings_resume_new_file)==False:
            os.makedirs(os.path.join(self.embeddings_resume_new_dir), exist_ok=True) 
            shutil.copy(self.example_resume_json_file, self.embeddings_resume_new_file)
        vector_dir_name = "vector"
        right_model=Embedding(root_dir=self.embeddings_resume_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name=vector_dir_name, doc_type="json", sentence_transformer=self.embeddings_model_name)
        right_model.build_index()
        #self.assertEqual(files_in_vector,1)
        vector_dir=os.path.join(self.embeddings_resume_dir, vector_dir_name)
        test_index=FAISS.load_local(vector_dir,self.embeddings_model,allow_dangerous_deserialization=True)
        similarity=test_index.similarity_search(query="Acme",k=1)
        #Check if the similarity's content contains "Acme Corporation"
        print(similarity)
        exists = similarity[0].page_content.find("Acme Corporation")
        self.assertGreaterEqual(exists, 0)


    def test_embedding_one_csv_file(self):
        # Copy the resume.json file to the test_data/new directory and build its index
        if os.path.exists(self.embeddings_knowledge_new_file)==False:
            os.makedirs(os.path.join(self.embeddings_knowledge_new_dir), exist_ok=True) 
            shutil.copy(self.example_insights_csv_file, self.embeddings_knowledge_new_file)
        vector_dir_name = "vector"
        right_model=Embedding(root_dir=self.embeddings_knowledge_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name=vector_dir_name, doc_type="csv", sentence_transformer=self.embeddings_model_name)
        right_model.build_index()
        #self.assertEqual(files_in_vector,1)
        vector_dir=os.path.join(self.embeddings_knowledge_dir, vector_dir_name)
        test_index=FAISS.load_local(vector_dir,self.embeddings_model,allow_dangerous_deserialization=True)
        similarity=test_index.similarity_search(query="Amazon",k=1)
        #Check if the similarity's content contains "Acme Corporation"
        print(similarity)
        exists = similarity[0].page_content.find("Amazon")
        self.assertGreaterEqual(exists, 0)

    def test_embedding_one_pdf_file(self):
        if os.path.exists(self.embeddings_resume_pdf_new_file)==False:
            os.makedirs(os.path.join(self.embeddings_resume_pdf_new_dir), exist_ok=True) 
            shutil.copy(self.example_resume_pdf_file, self.embeddings_resume_pdf_new_file)
        vector_dir_name = "vector"
        right_model=Embedding(root_dir=self.embeddings_resume_pdf_dir, new_dir_name="new", processed_dir_name="processed",
                      vector_dir_name=vector_dir_name, doc_type="pdf", sentence_transformer=self.embeddings_model_name)
        right_model.build_index()
        vector_dir=os.path.join(self.embeddings_resume_pdf_dir, vector_dir_name)
        test_index=FAISS.load_local(vector_dir,self.embeddings_model,allow_dangerous_deserialization=True)
        similarity=test_index.similarity_search(query="Honswer",k=1)
        print(similarity)
        exists = similarity[0].page_content.find("Honswer")
        self.assertGreaterEqual(exists, 0)

    def test_append_json_data(self):
        file = File(self.test_dir, 'example.json')
        file.create_or_load()
        file.append_to_file(self.append_data)
        loaded_data = file.getJSONContent()
        self.assertEqual(loaded_data, self.append_data)

    def test_append_txt_data(self):
        file = File(self.test_dir, 'example.txt')
        file.create_or_load()
        file.append_to_file(json.dumps(self.append_data))
        loaded_data = file.getContent()
        self.assertIn(self.append_data['key1'], loaded_data)

    def tearDown(self):
            # Remove the test directory and its contents after testing
            shutil.rmtree(self.test_dir)

class TestJobPost(unittest.TestCase):
    def setUp(self):
        self.created_files=[]

    def test_create_JobPost_from_file(self):
        job_post=create_job_from_file(EXAMPLE_JOB_POST_PATH)
        self.assertIn('AMAI',job_post.history.initial_job_post)        
    
    def test_create_replace_JobPost_CL(self):
        job_post = JobPost()
        self.assertTrue(os.path.exists(job_post.file.filepath),"Failure to create new JobPost file")

        # Test storing and retrieving cover letter
        test_cover_letter_content="Dear Hiring Manager,\n\nI am excited to apply for the position at AMAI as a dedicated and talented individual with a strong background in product management, business analysis, and project management. My diverse experience in IT projects and products, ranging from top consulting firms to startups, has equipped me with the skills necessary to excel in a multicultural environment like AMAI.\n\nIn my current role at dst, I have managed multiple vendors for SaaS B2B CX/EX solutions, demonstrating my ability to develop and implement innovative strategies to position products in the market successfully. Additionally, as the founder of sdg, I have grown the user base from 0 to over 5,000 users in just three months by implementing creative marketing concepts and leveraging low-code automation.\n\nMy passion for AI and machine learning, combined with my experience in developing AI agents and assistants to optimize job searches and applications, aligns perfectly with AMAI's goal of shaping the future of artificial intelligence. I have honed my communication skills through working with AI technologies, tailoring my messaging to different audiences effectively.\n\nFurthermore, my experience in leading projects, coordinating resources, and identifying partnership opportunities will enable me to take on the responsibilities outlined in the job post with confidence. I am a team player who thrives in collaborative environments and enjoys working with interdisciplinary teams to develop innovative solutions.\n\nI am particularly drawn to AMAI's commitment to advancing the field of artificial intelligence and creating innovative applications for various industries. My background in AI, product management, and business intelligence aligns well with AMAI's values and mission, making me a strong candidate for this role.\n\nThank you for considering my application. I am eager to bring my skills and expertise to AMAI and contribute to the company's success.\n\nBest regards,\n[Your Name]"
        job_post.store_cover_letter(test_cover_letter_content)
        job_post.create_or_load_application_directory()
        #Includes JobPost.update_history()
        job_post2=JobPost(job_post.history.id)
        self.assertEqual(job_post2.history.cover_letter.current_body,test_cover_letter_content,"Failure to store/retrieve cover letter")        
        self.assertIsNotNone(job_post2.history.cover_letter.directory,"Failure to store/retrieve cover letter directory")
        self.created_files.append(job_post.file.filepath)

    def test_add_salient_points_to_history(self):
        # Create a list of salient points
        highest_score_salient_point_text = "Partner with M365 applications teams"
        file_handler = File(directory=EXAMPLE_FILES_DIR, name='salientpoints.json')
        salient_points=file_handler.getJSONContent()
        
        # Call the function
        job_post=JobPost()
        job_post.add_salient_points_to_history(salient_points)
   
        # Verify that the salient point list was updated correctly
        first_written_point=job_post.history.salient_points[0]
        self.assertEqual(first_written_point.point,highest_score_salient_point_text,"Failed to add or sort salient points to history")
        self.assertIsNone(first_written_point.insights,"Failed to add insights node to salient point")

        self.created_files.append(job_post.file.filepath)
   
    def test_parse_load_job_post_and_derive_salient_points(self):
        # Caution: Calls AI 
        job_post = JobPost()
        job_post_doc=File(EXAMPLE_FILES_DIR, "job_post.txt")
        job_post_doc.load('r')
        job_post_txt=job_post_doc.content
        job_post.parse_job_post(job_post_txt)
        history_file_path=job_post.file.filepath
        self.assertTrue(os.path.exists(history_file_path),"History file not created")
        history_file=File(job_post.file.directory,job_post.file.name)
        history_file.load('r')
        history_file_content=history_file.JSONcontent
        self.assertEqual(history_file_content['job_characteristics']['organization'], "AMAI","Wrong organization or organization not present in the history file")
        job_post2=JobPost(job_post.history.id)
        job_post2.load_job_post()
        self.assertEqual(job_post2.file.name,job_post.file_name,"Failure to load pre-existing job post's file")
        self.assertEqual(job_post2.history.initial_job_post,job_post_txt,"Failure to load pre-existing job post's attributes")
        salient_points=job_post2.derive_salient_points()
        self.assertGreaterEqual(len(salient_points),1,"Failure to derive salient points")
        self.created_files.append(job_post.file.filepath)
        
    def tearDown(self):
        unique_files=list(set(self.created_files))
        for file in unique_files:
            os.remove(file)
        # print("remember to uncomment tear down")

class TestTemplating(unittest.TestCase):
    def setUp(self):
        self.created_files=[]
    '''
    def test_merge_doc_file_to_pdf(self):
        template_file_path = os.path.join(example_files_dir,"cl_template.docx")
        output_file_dir = test_data_dir
        output_file_name = "merged"
        output_docx_name=output_file_name+'.docx'
        output_pdf_name=output_file_name+'.pdf'
        context = {"cover_letter_body": "Test text"}

        docx_file=merge_doc_file(template_file_path, output_file_dir, output_docx_name, context)
        assert os.path.exists(os.path.join(output_file_dir, output_docx_name))
        self.created_files.append(docx_file.filepath)
        
        pdf_input_path=os.path.join(output_file_dir, output_docx_name)
        pdf_output_path=os.path.join(output_file_dir, output_pdf_name)
        pdf_file=convert_docx_to_pdf(pdf_input_path,pdf_output_path,output_pdf_name)
        assert os.path.exists(os.path.join(output_file_dir, output_pdf_name))
        self.created_files.append(pdf_file.filepath)
    '''
    
    def test_merge_md_file_to_pdf(self):
        template_file_path = os.path.join(EXAMPLE_FILES_DIR,"cl_template.md")
        output_file_dir = TEST_DATA_DIR
        output_file_basename = "merged"
        context = {"cover_letter_body": "Test text","organization": "AMAI","position":"Test position","date":"April, 17, 2024"}
        merged_file=merge_file(template_file_path, output_file_dir, output_file_basename, context)
        assert os.path.exists(os.path.join(output_file_dir, (output_file_basename+'.md')))

        self.created_files.append(merged_file.filepath)
        
        pdf_input_path=os.path.join(output_file_dir, (output_file_basename+'.md'))
        pdf_output_path=os.path.join(output_file_dir, output_file_basename)
        pdf_file=convert_to_pdf(pdf_input_path,pdf_output_path,output_file_basename)
        assert os.path.exists(os.path.join(pdf_output_path, output_file_basename+'.pdf'))
        self.created_files.append(pdf_file.filepath)

        
    def tearDown(self):
        unique_files=list(set(self.created_files))
        for file in unique_files:
            os.remove(file)
        
if __name__ == '__main__':
    unittest.main()
    
class TestAirtable(unittest.TestCase):
    def setUp(self):
        self.settings=Preferences('settings_files')
        self.exclude_airtable_tests=not self.settings.use_airtable
        if self.exclude_airtable_tests:
            return
        self.created_files=[]
        self.created_records=[]
        self.airtable_connection=AirtableConnection()
    
    def test_create_find_remove_airtable_job(self):
        if self.exclude_airtable_tests:
            return
        TEST_JTS_ID='test_id'

        self.assertIsNotNone(self.airtable_connection,"Failed to create Airtable connection")
        new_job=self.airtable_connection.add_job_post(jts_id=TEST_JTS_ID,job_post_details='test job details',organization='test organization', status='Test', source='test.py')
        self.assertIsNotNone(new_job['id'],"Failed to create new job in Airtable")
        found_job=self.airtable_connection.find_job_post(jts_id=TEST_JTS_ID)
        self.assertIsNotNone(found_job['id'],"Failed to find created job in Airtable")
        self.created_records.append(found_job)
            
    def test_parse_airtable_records_for_parsing(self):
        # Caution: Calls AI 
        if self.exclude_airtable_tests:
            return
        no_rec_for_parsing=parse_airtable_records_for_parsing(self.settings)
        self.assertEqual(len(no_rec_for_parsing),0,"Error retrieving no records for parsing from Airtable")        
        job_without_post_details=self.airtable_connection.add_job_post(organization='test organization', status=self.settings.for_parsing_status, source='test.py') #Should be imported but not parsed, since there is not parser available
        self.created_records.append(job_without_post_details)          
        job_with_post_details=self.airtable_connection.add_job_post(job_post_details='test job details',organization='test organization', status=self.settings.for_parsing_status, source='test.py')
        self.created_records.append(job_with_post_details)                    
        imported_jobs=parse_airtable_records_for_parsing(self.settings)
        
        for imported_job in imported_jobs:
            self.created_files.append(imported_job.file)
            
        self.assertEqual(len(imported_jobs),2,"Failed to import job post from Airtable")
    
    def tearDown(self) -> None:
        unique_files=list(set(self.created_files))
        for file in unique_files:
            os.remove(file.filepath)
        for record in self.created_records:
            self.airtable_connection.delete_job_post(airtable_id=record['id'])            
   