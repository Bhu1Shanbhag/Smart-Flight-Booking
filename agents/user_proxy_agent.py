import json

class UserProxyAgent:
    """
    Agent responsible for presenting information to the HR user and gathering constraints.
    """
    
    def process_strategy_feedback(self, strategy: dict, user_input: str) -> dict:
        """
        Processes user feedback on a proposed strategy using the LLM to classify intent.
        """
        
        user_input_lower = user_input.strip().lower()
        if user_input_lower in ['proceed', 'yes', 'y', 'ok', 'approve']:
            return {"status": "approved", "new_constraints": {}}
            
        import asyncio
        import os
        from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
        from autogen_core.models import SystemMessage, UserMessage
        
        async def interpret_feedback():
            try:
                model_client = AzureOpenAIChatCompletionClient(
                    azure_endpoint=os.environ.get("AOAI_CHAT_ENDPOINT"),
                    model=os.environ.get("AOAI_CHAT_DEPLOYMENT"),
                    api_version=os.environ.get("AOAI_API_VERSION", "2024-08-01-preview"),
                    api_key=os.environ.get("AOAI_CHAT_KEY")
                )
                prompt = (
                    "You are a travel assistant evaluating user feedback on a proposed itinerary. "
                    "Determine if the user is approving the itinerary (even if they add remarks like 'proceed with hotel') "
                    "or if they are providing new constraints (e.g., 'can't leave before 8am', 'need to arrive later'). "
                    "Return ONLY the word 'approved' or 'modified'."
                )
                messages = [
                    SystemMessage(content=prompt),
                    UserMessage(content=f"User input: '{user_input}'", source="user")
                ]
                response = await model_client.create(messages)
                return response.content.strip().lower()
            except Exception:
                # Fallback to simple matching
                if "proceed" in user_input_lower or "approve" in user_input_lower:
                    return "approved"
                return "modified"
                
        intent = asyncio.run(interpret_feedback())
        
        if intent == "approved":
            return {"status": "approved", "new_constraints": {}}
            
        print(f"[UserProxyAgent] Parsed user feedback into constraints...")
        return {
            "status": "modified",
            "new_constraints": {"user_note": user_input}
        }
        
    def process_final_approval(self, itinerary: dict, user_input: str) -> bool:
        """
        Processes final itinerary approval.
        """
        return user_input.strip().lower() in ['approve', 'yes', 'y', 'ok']
