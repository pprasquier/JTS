import logging
import os
from pyairtable import Api
from pyairtable.formulas import *
from prefy import PreferencesWrapper


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')

  
class AirtableConnection(PreferencesWrapper):  
    class AirtableTable:
        def __init__(self, connection,table_id):
            self.table_id=table_id
            self.table=connection.api.table(connection.settings.airtable_base_id,table_id)
            self.records=[]
            
        def get_all_records(self,view_id=None) -> list:
            try:
                records=self.table.all(view=view_id)
                return records
            except Exception as e:
                logging.error('Error {} .'.format(e))
            raise Exception
        
        def get_record_by_id(self,record_id) -> dict:
            try:
                records=self.table.get(record_id)
                return records
            except Exception as e:
                logging.error('Error {} .'.format(e))
            raise Exception 
        
        def get_records_by_match(self,match_conditions,sort_fields=[],view_id=None) -> list:
            try:
                formula=match(match_conditions)
                records=self.table.all(formula=formula,sort=sort_fields,view=view_id)
                return records
            except Exception as e:
                logging.error('Error {} .'.format(e))
            raise Exception      
               
        def get_records_by_search(self,searched_value,within_field_name,sort_fields=[]) -> list:
            try:
                formula=f"find('{searched_value}',arrayjoin({{{within_field_name}}}))"
                records=self.table.all(formula=formula,sort=sort_fields)
                return records
            except Exception as e:
                logging.error('Error {} .'.format(e))
            raise Exception             
    class JobTable(AirtableTable):
        def __init__(self, connection, table_id):
            super().__init__(connection=connection, table_id=table_id)           
           
    def __init__(self,settings=None):
        super().__init__(settings=settings)
        if not self.settings.use_airtable:
            logging.info("Airtable not used")
            return None
        self.api = Api(os.environ['AIRTABLE_API_KEY'])
        self.base = self.api.base(self.settings.airtable_base_id)
        self.job = self.JobTable(connection=self,table_id=self.settings.job_table_id)
        if self.settings.use_airtable_resume:
            self.individual=self.AirtableTable(connection=self,table_id=self.settings.individual_table_id)
            self.languages=self.AirtableTable(connection=self,table_id=self.settings.language_table_id)
            self.experiences=self.AirtableTable(connection=self,table_id=self.settings.experience_table_id)
            self.certifications=self.AirtableTable(connection=self,table_id=self.settings.certification_table_id)
            self.skills=self.AirtableTable(connection=self,table_id=self.settings.skill_table_id)
            self.tasks=self.AirtableTable(connection=self,table_id=self.settings.task_table_id)
            self.translations=self.AirtableTable(connection=self,table_id=self.settings.translation_table_id)
        if self.settings.use_airtable_knowledge:
            self.knowledge=self.AirtableTable(connection=self,table_id=self.settings.knowledge_table_id)
        
    def add_job_post(self, jts_id=None,job_post_details=None,organization=None,status=None,source=None):
       #Adds a new job post to airtable
        try:
            new_job=self.job.table.create({
                self.settings.jts_id_field_name:jts_id,
                self.settings.organization_field_name:organization,
                self.settings.status_field_name:status,
                self.settings.source_field_name:source,
                self.settings.job_description_field_name:job_post_details
            })
            logging.info('New job post added to airtable: {}'.format(new_job['id']))
            return new_job
            
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception

    def find_job_post(self, jts_id):
        #Finds a job post in airtable by its jts_id
        try:
            formula=match({self.settings.jts_id_field_name: jts_id})
            found_job=self.job.table.first(formula=formula)
            return found_job
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
       
    def delete_job_post(self, airtable_id):
        #Deletes a job post in airtable by its airtable_id. Mostly used for testing purposes.
        try:
            self.job.table.delete(airtable_id)
            logging.info('Job post deleted from airtable: {}'.format(airtable_id))
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
       
    def retrieve_job_posts(self,view_id=None) -> list:
        try:
            records=self.job.table.all(view=view_id)
            return records
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
       
    def update_job_status(self,record_id,status):
        try:
            kwargs={self.settings.status_field_name:status}
            self.update_job_post(record_id,**kwargs)
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception

    def update_job_post(self,record_id,**kwargs):
        try:
            self.job.table.update(record_id,kwargs)
            logging.info('Job post updated in airtable: {}'.format(record_id))
        except Exception as e:
           logging.error('Error {} .'.format(e))
           raise Exception
       
if __name__ == "__main__":
    airtable_connection=AirtableConnection()
    jobs=airtable_connection.retrieve_job_posts()
    print (len(jobs))