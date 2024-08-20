import os
import json
import logging
import shutil

from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader,CSVLoader
from langchain_community.document_loaders.pdf import PyPDFLoader as PDFLoader
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores.faiss import FAISS
import pandas as pd
from JSONLoader import JSONLoader
from datetime import datetime
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')

def flatten_json(json_obj, parent_key='', sep='_'):
    """
    Flatten a complex nested JSON object including lists of objects.

    Args:
        json_obj (dict or list): The JSON object to flatten.
        parent_key (str): The key of the parent JSON object (used for recursion).
        sep (str): Separator used to concatenate keys.

    Returns:
        dict: Flattened JSON object.
    """
    items = {}
    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                items.update(flatten_json(value, new_key, sep=sep))
            else:
                items[new_key] = value
    elif isinstance(json_obj, list):
        for i, item in enumerate(json_obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            if isinstance(item, (dict, list)):
                items.update(flatten_json(item, new_key, sep=sep))
            else:
                items[new_key] = item
    return items

class File:
    def __init__(self, directory: str=None, name: str=None,filepath: str=None):

        if filepath is None:

            self.directory = directory
            self.name = name
            self.filepath=os.path.join(self.directory, self.name)
        else:
            self.filepath=filepath
            self.name=os.path.basename(self.filepath)
            self.directory=os.path.dirname(self.filepath)
        if '.' not in self.name:
            logging.error("No extension in file name {}".format(self.name))
            raise ValueError("Name must contain an extension (e.g.: .json")
            exit()
        self.extension=self.name.rsplit('.',1)[1]
        self.loaded=False
        self.content=None
        self.JSONcontent=None

    def load(self,mode):
        # Configure logger
        
        # Check if directory and file exist
        if not os.path.exists(self.filepath):
            logging.error("File '{}' does not exist in directory '{}'.".format(self.name, self.directory))
            raise FileNotFoundError

        # Try to load file
        try:
            self.mode=mode
            file=open(self.filepath, mode)
            logging.info("File '{}' loaded successfully.".format(self.name))
            self.file=file

            if self.mode=='r':
                self.content=file.read()
                # If the file has content and is json 
                if self.content!='':
                    match self.extension:
                        case 'json':
                            self.JSONcontent = json.loads(self.content)            
                self.loaded=True
                self.file.close()
            return self.file
        except json.JSONDecodeError:
            logging.error("Invalid JSON format in file '{}'.".format(self.name))
            return None
        except Exception as e:
            logging.error("Error '{}' parsing file '{}'.".format(e,self.name))
            raise Exception

    #
    def create_or_load(self):
       
        # Check if file exists
        if os.path.exists(self.filepath):
            logging.info("File '{}' already exists. Loading...".format(self.name))
            self.mode='r'
            self.file=self.load(mode=self.mode)
            return self.file
        else:
            logging.info("File '{}' does not exist. Creating...".format(self.name))
            try:
                # Create file
                self.mode='w'
                with open(self.filepath, self.mode) as file:
                    self.file=file
                    return self.file
            except FileNotFoundError:
                logging.error("Directory '{}' does not exist.".format(self.directory))
            except Exception as e:
                logging.error("Error occurred while creating file '{}': {}".format(self.name, e))
                raise Exception

    def write_to_file(self,data):
        try:
            with self.load('w') as file:  # Force open in write mode to make sure the file is cleared before writing
                if self.extension=='json':
                    json.dump(data, file)
                else:
                    file.write(data)
            logging.info("Successfully wrote to file: {}".format(self.name))
        except TypeError as e:
            logging.error("TypeError writing to file '{}': {}".format(self.name, e))
            raise Exception            
        except Exception as e:
            logging.error("Error writing to file '{}': {}".format(self.name, e))
            raise Exception

    def append_to_file(self,data):
        try:
            if self.extension=='json':
                self.load('r')  # Make sure JSONcontent is updated
                # Update existing data with new data
                if self.JSONcontent == None:
                    self.JSONcontent = data
                else:
                    self.JSONcontent.update(data)
                self.write_to_file(self.JSONcontent)

            else:
                if self.mode!='a' or self.file.closed:
                    self.file.close()
                    self.load('a')
                self.file.write(data)

            self.load('r')  # Update content/JSONcontent
            logging.info("Successfully appended to file: {}".format(self.name))
        except Exception as e:
            logging.error("Error appending to file '{}': {}".format(self.name, e))
            raise Exception

    def getContent(self):
        if self.loaded==False:
            self.load('r')
        return self.content
    
    def getJSONContent(self):
        if self.loaded==False:
            self.load('r')
        return self.JSONcontent
    
class Embedding:
    def __init__(self, root_dir, new_dir_name,processed_dir_name,vector_dir_name,doc_type,sentence_transformer,**kwargs):
        """
        Initiates an Embeddings directory.

        Parameters:
        - root_dir: str
            A string representing the path to the parent directory for the documents
        - new_dir_name: str
            The name of the directory that stores new documents for future vectorizing. It must be immediately below the root_directory
        - processed_dir_name: str
            The name of the directory that stores documents that have been vectorized. It will be searched or created immediately below the root_directory
        - vector_dir_name: str
            The name of the directory that stores vectors. It will be searched or created immediately below the root_directory
        - doc_type: str
            A directory can only contain documents of a single doc_type. It defines the type of loader used for vectorizing. Allowed values are: 'json | csv | pdf'
        - sentence_transformer: str
            The name of the model to be used for parsing text

        Raises:
        - ValueError: If doc_type is not allowed.
        - FileNotFoundError: If root_dir does not exist

        Returns:
        - The Embedding object
        """
        
        try:
            #A directory can only contain documents of a single doc_type. These will define the type of loader used for vectorizing
            match doc_type:
                case 'json':
                    self.loader=JSONLoader
                case 'md':
                    self.loader=UnstructuredMarkdownLoader
                case 'pdf':
                    self.loader=PDFLoader
                case 'txt':
                    self.loader=TextLoader
                case 'csv':
                    self.loader=CSVLoader
                case 'misc':
                    pass
                case _:
                    logging.error("Doc_type {} is not supported.".format(doc_type))
                    raise ValueError(f"Doc_type '{doc_type}' is not supported.")
            
            if os.path.exists(root_dir) == False:
                logging.error("Path {} does not exist.".format(root_dir))
                raise FileNotFoundError(f"Path '{root_dir}' does not exist.")      
            
            self.doc_type = doc_type
            self.root_directory = root_dir
            self.new_directory=os.path.join(self.root_directory, new_dir_name)
            self.processed_directory=os.path.join(self.root_directory, processed_dir_name)
            self.vector_directory=os.path.join(self.root_directory, vector_dir_name)
            self.sentence_transformer = SentenceTransformerEmbeddings(model_name=sentence_transformer)
            for key, value in kwargs.items():
                setattr(self, key, value)
        except OSError:
            logging.error("Invalid embedding model: {}".format(sentence_transformer))
            raise OSError
        except Exception:
            logging.error("Error initializing Embedding object.")
            raise Exception
        
    def build_index(self,mode='replace'):
        try:
            if mode not in ['replace']:
                #TODO: Add support for other 'append'
                logging.error("Invalid build mode: {}".format(mode))
                raise ValueError(f"{mode} is not a valid build mode.")

            #Are there files?
            self.new_files_count = 0
            self.new_files=[]
            for file in os.listdir(self.new_directory):
                if file.endswith(self.doc_type) and os.path.isfile(os.path.join(self.new_directory, file)):
                    self.new_files_count += 1
                    self.new_files.append(os.path.join(self.new_directory,file))
            if self.new_files_count==0:
                logging.info("No files of type {} to index in: {}".format(self.doc_type,self.new_directory))
                return 0   
                    
            #Create or retrieve the vector and processed directories
            os.makedirs(self.vector_directory,exist_ok=True)
            os.makedirs(self.processed_directory,exist_ok=True)

            #If mode='replace', then the content of the vector directory will be deleted before building the index
            if mode=='replace':
                shutil.rmtree(self.vector_directory)
                logging.info("Removed vector directory: {}".format(self.vector_directory))

            #Build the index for each new file, save to the vector directory and move the processed files to the processed directory
            
            logging.info("Poplulating vector store with {} docs".format(self.new_files_count))
            files_processed = 0
            self.temp_files_dir = os.path.join(self.processed_directory, 'tmp')
            os.makedirs(self.temp_files_dir,exist_ok=True)
            output_files = []
            vectorstores=[]
            for new_file in self.new_files:
                match self.doc_type:
                    case 'json':
                        # Iterate through the first nodes of the new file
                        # If the value is a list, then flatten it using flatten_json and store the result in a new JSON file named with the key of the node
                        # If the value is not a list, then store the value in a new JSON file named with the key
                        # Once all first nodes have been processed, call vectorize each of the new JSON files through the _vectorize_json method
                        with open(new_file, 'r') as file:
                            data = json.load(file)
                            # Iterate over the keys and create separate JSON objects
                            separate_objects = {}
                            for key in data:
                                separate_objects[key] = {key: data[key]}

                            # Write each JSON object to a separate file
                            for key, value in separate_objects.items():
                                flattened=flatten_json(value,"","|")
                                with open(os.path.join(self.temp_files_dir,f'{key.lower()}.json'), 'w') as output_file:
                                    json.dump(flattened, output_file, indent=4) 
                                    output_files.append(output_file)
                            new_json_vectors=self._vectorize_json_files(output_files)
                            vectorstores.extend(new_json_vectors)                                                                
                    case 'csv':
                        if hasattr(self,'csv_args'):
                            self.loader=CSVLoader(file_path=new_file,csv_args=self.csv_args)
                        else:
                            self.loader=CSVLoader(file_path=new_file)

                        data=self.loader.load()
                        vectorstore = FAISS.from_documents(data, self.sentence_transformer)
                        vectorstores.append(vectorstore)
                    case 'pdf':
                        self.loader=PDFLoader(file_path=new_file)
                        data=self.loader.load()
                        vectorstore = FAISS.from_documents(data, self.sentence_transformer)
                        vectorstores.append(vectorstore)
                    case _:
                        # TBC
                        raise ValueError(f"Doc_type '{self.doc_type}' is not supported yet.")
                
                
                # Rename the processed file to include date so as to allow for processing files with the same name
                # And move to the processed directory
                
                self.merge_and_save_vectorbases(vectorstores)
                iso_date = str(datetime.now().timestamp())
                new_file_name = iso_date+'_'+os.path.basename(new_file)
                os.rename(new_file,os.path.join(self.processed_directory, new_file_name))
                logging.info("Moved file {} to: {}".format(new_file_name,self.processed_directory))
                files_processed += 1

            return files_processed
            #The loader settings depend on the type of document
        except FileNotFoundError as e:
            logging.error("Error '{}' while building index".format(e,self.new_directory))
            raise FileNotFoundError
        except Exception as e:
            logging.error("Error '{}' while building index from '{}'.".format(e,self.new_directory))
            raise Exception 

    def load_index(self):
        self.store=VectorStore(self.vector_directory,sentence_transformer=self.sentence_transformer)
    
    def _vectorize_json_files(self, files):
        vectorstores=[]
        for file in files:
            loader=JSONLoader(file_path=file.name)
            doc = loader.load()
            vectorstore = FAISS.from_documents(doc, self.sentence_transformer)
            vectorstores.append(vectorstore)
        
        return vectorstores
    def merge_and_save_vectorbases(self, vectorstores):
        if len(vectorstores) > 1:
            for vectorstore in vectorstores[1:]:
                vectorstores[0].merge_from(vectorstore)

        vectorstores[0].save_local(self.vector_directory)
        logging.info("Saved FAISS to: {}".format(self.vector_directory))


    def get_docs_length(self):
        index = FAISS.load_local(self.vector_directory,embeddings=self.sentence_transformer)
        dict = index.docstore._dict
        return len(dict.values()) 


class VectorStore:
    def __init__(self,store_path,sentence_transformer="all-mpnet-base-v2"):
            if isinstance(sentence_transformer,HuggingFaceEmbeddings):
                self.sentence_transformer = sentence_transformer
            else:                
                self.sentence_transformer = SentenceTransformerEmbeddings(model_name=sentence_transformer)
            self.db = FAISS.load_local(store_path,self.sentence_transformer,allow_dangerous_deserialization=True)
            v_dict=self.db.docstore._dict
            data_rows=[]
            for k in v_dict.keys():
                doc_name=v_dict[k].metadata['source'].split('/')[-1]
                content = v_dict[k].page_content
                data_rows.append({"chunk_id":k,"document":doc_name,"content":content})
            self.df=pd.DataFrame(data_rows)
            self.doc_count=data_rows.__len__()

    def display(self):
        print(self.df)

