import asyncio
import os
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class WebSurferPlugin:
    """
    A Semantic Kernel plugin that wraps the Magentic-One / AutoGen Web Surfer Agent.
    """
    
    @kernel_function(
        description="Searches the web for flight information, summarizes the best options, and returns them.",
        name="search_flights_on_web"
    )
    def search_flights_on_web(self, query: str) -> str:
        """
        Executes a web search for flights using the MultimodalWebSurfer.
        This function runs the async workflow synchronously to fit within the standard SK function call.
        """
        return asyncio.run(self._run_web_surfer_async(query))
        
    async def _run_web_surfer_async(self, query: str) -> str:
        """
        Internal async method to execute AutoGen Web Surfer.
        """
        from autogen_ext.agents.web_surfer import MultimodalWebSurfer
        from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
        from autogen_agentchat.teams import RoundRobinGroupChat
        
        model_client = AzureOpenAIChatCompletionClient(
            model=os.environ.get("AOAI_CHAT_DEPLOYMENT", "gpt-4o"),
            azure_endpoint=os.environ.get("AOAI_CHAT_ENDPOINT"),
            azure_deployment=os.environ.get("AOAI_CHAT_DEPLOYMENT"),
            api_version=os.environ.get("AOAI_API_VERSION_GPT"),
            api_key=os.environ.get("AOAI_CHAT_KEY")
        )
        web_surfer = MultimodalWebSurfer(name="WebSurfer", model_client=model_client, headless=False)
        team = RoundRobinGroupChat([web_surfer], max_turns=15)
        
        print(f"[WebSurferPlugin] Starting Magentic-One web surfer for query: {query}")
        try:
            # Enforce a 180-second maximum timeout on the web surfer to allow for slow multimodal processing
            result = await asyncio.wait_for(team.run(task=query), timeout=180.0)
            return str(result.messages[-1].content)
        except asyncio.TimeoutError:
            print("[WebSurferPlugin] Web Surfer timed out (180s limit reached).")
            raise ValueError("Web Surfer timed out.")
