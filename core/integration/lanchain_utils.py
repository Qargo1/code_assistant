from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.chains import LLMChain

class CodeAssistantAgent:
    def __init__(self):
        self.llm = OpenAI(temperature=0.3)
        self.tools = self._init_tools()
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent="conversational-react-description",
            verbose=True
        )

    def _init_tools(self):
        return [
            Tool(
                name="WebSearch",
                func=self.web_search,
                description="Useful for finding up-to-date information"
            ),
            Tool(
                name="Terminal",
                func=self.execute_terminal,
                description="Execute terminal commands with user approval"
            )
        ]

    def process_query(self, query: str, chat_history: list) -> str:
        return self.agent.run(
            input=query,
            chat_history=chat_history
        )