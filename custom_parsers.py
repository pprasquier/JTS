from langchain_core.output_parsers import StrOutputParser
import json

class StrOutputParser(StrOutputParser):
 def parse(self, text) -> str:
    try:
        # Check if the input is a string
        if isinstance(text, (str, bytes, bytearray)):
            try:
                # Try to parse the text as JSON
                data = json.loads(text)
            except json.JSONDecodeError:
                # If it's not JSON, use the default parse method
                return super().parse(text)
        # Check if the input is already a dictionary
        elif isinstance(text, dict):
            data = text
        else:
            # If it's neither, use the default parse method
            return super().parse(text)
        
        # Extract the content of the "answer" or "content" field if present
        if 'answer' in data:
            return data['answer']
        elif 'content' in data:
            return data['content']
        elif 'response' in data:
            return data['response']
        else:
            # If neither field is present, use the default parse method
            return super().parse(text)
    except Exception as e:
        raise e

