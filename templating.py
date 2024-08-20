import os
import logging

from file_handler import File

""" Abandoned doc templating as it has too many dependencies and is unreliable.
def merge_doc_file(template_file_path,output_file_dir,output_file_name,context):
    from docxtpl import DocxTemplate
    
    try:
        doc = DocxTemplate(template_file_path)
        doc.render(context)
        output_file_path=os.path.join(output_file_dir,output_file_name)
        doc.save(output_file_path)
        merged_file=File(output_file_dir,output_file_name)
        return merged_file
        
    except Exception as e:
     logging.error('Error {} .'.format(e))
     raise Exception 
     
    def convert_docx_to_pdf(input_file_path,output_file_dir,output_file_name):
    try:
        import docx2pdf
        docx2pdf.convert(input_file_path,output_file_dir)
        pdf_file=File(output_file_dir,output_file_name)
        logging.info("Created final cover letter at {}".format(output_file_dir))

        return pdf_file
    except Exception as e:
     logging.error('Error {} .'.format(e))
     raise Exception
     
     
     """

def merge_file(template_file_path,output_file_dir,output_file_basename,context,extension='.html'):
    from jinja2 import Template
    import codecs
    
    try:
        with open(template_file_path, 'r') as file:
            template = Template(file.read(),trim_blocks=False)
        rendered_file = template.render(context)
        output_file_name=output_file_basename+extension
        os.makedirs(output_file_dir,exist_ok=True)
        output_file_path=os.path.join(output_file_dir,output_file_name)
        output_file = codecs.open(output_file_path, "w", "utf-8")
        output_file.write(data=rendered_file)
        output_file.close()
        merged_file=File(output_file_dir,output_file_name)
        logging.info("Created intermediary file at {}".format(output_file_path))
        return merged_file
        
    except Exception as e:
     logging.error('Error {} .'.format(e))
     raise Exception


 
def convert_to_pdf(input_file_path,output_file_dir,output_file_basename,format='markdown',engine='pdfkit',**kwargs):
    try:

        if not os.path.exists(output_file_dir):
            os.makedirs(output_file_dir)
        
        extra_args=['-V', 'geometry:margin=2cm']
        if format=='docx':
            extra_args.append('-f')
            extra_args.append('docx+styles')
        output_file_name=output_file_basename+'.pdf'
        output_file_path=os.path.join(output_file_dir,output_file_name)
        # if engine=='pypandoc' or format=='markdown':
        #     from pypandoc import convert_file            
        #     convert_file(input_file_path,'pdf',format,outputfile=output_file_path,extra_args=extra_args)
        if engine=='pdfkit':
            import pdfkit
            options={
                'dpi': 600,
                
            }
            pdfkit.from_file(input_file_path,output_file_path, options=options)
        pdf_file=File(output_file_dir,output_file_name)
        logging.info("Created pdf file {} in {}".format(output_file_name, output_file_dir))
        return pdf_file
    except Exception as e:
     logging.error('Error {} .'.format(e))
     raise Exception