import logging
from langchain.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import initialize_agent, AgentType
from utils import instantiate_settings_llm
from langchain import hub

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s -  %(filename)s - %(lineno)d - %(message)s')

llm=instantiate_settings_llm('enrich')

search = TavilySearchAPIWrapper()
tavily_tool = TavilySearchResults(api_wrapper=search)

# initialize the agent
agent_chain = initialize_agent(
    [tavily_tool],
    llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)

def enrich_from_web(topic):
    response = agent_chain.run(topic)
    return response

if __name__ == '__main__':
    # You can replace 'AI technology' with any topic you'd like to search for.
    topic = 'What should someone applying for the role of product manager for product Gmail at Google know?'
    result = enrich_from_web(topic)
    print(result)