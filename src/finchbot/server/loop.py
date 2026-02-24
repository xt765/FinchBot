import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from finchbot.channels.bus import MessageBus
from finchbot.channels.schema import OutboundMessage, InboundMessage
from finchbot.config.schema import Config
from finchbot.agent.factory import AgentFactory

class AgentLoop:
    """Core loop connecting MessageBus and LangGraph Agent."""
    
    def __init__(self, bus: MessageBus, config: Config, workspace: Path):
        self.bus = bus
        self.config = config
        self.workspace = workspace
        self.agents: Dict[str, Any] = {} # session_key -> agent_graph
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the agent loop."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AgentLoop started")

    async def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AgentLoop stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                # Consume message
                msg = await self.bus.consume_inbound()
                
                # Process concurrently
                asyncio.create_task(self._process_message(msg))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in AgentLoop: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, msg: InboundMessage) -> None:
        session_id = msg.session_key
        logger.info(f"Processing message for session: {session_id}")
        
        try:
            # 1. Get or create agent
            # Since create_for_cli is sync, run in thread
            agent = await self._get_or_create_agent(session_id)
            
            # 2. Prepare inputs
            # TODO: Handle media/files if supported
            inputs = {"messages": [HumanMessage(content=msg.content)]}
            run_config = {"configurable": {"thread_id": session_id}}
            
            # 3. Invoke Agent
            response_content = ""
            
            # Streaming approach to capture final response
            async for event in agent.astream(inputs, config=run_config):
                # event is usually Dict[NodeName, StateUpdate]
                for node_name, state_update in event.items():
                    if "messages" in state_update:
                        messages = state_update["messages"]
                        if isinstance(messages, list) and messages:
                            last_msg = messages[-1]
                            if isinstance(last_msg, AIMessage):
                                response_content = last_msg.content

            # 4. Send response
            if response_content:
                out_msg = OutboundMessage(
                    target_channel=msg.channel,
                    target_id=msg.chat_id,
                    content=str(response_content),
                    reply_to=None 
                )
                await self.bus.publish_outbound(out_msg)
            else:
                logger.warning(f"No response content generated for session {session_id}")

        except Exception as e:
            logger.exception(f"Error processing message {session_id}: {e}")
            # Optionally send error message back to user

    async def _get_or_create_agent(self, session_id: str) -> Any:
        async with self._lock:
            if session_id in self.agents:
                return self.agents[session_id]
            
            # Use async factory
            result = await self._create_agent(session_id)
            
            agent = result[0]
            self.agents[session_id] = agent
            return agent

    async def _create_agent(self, session_id: str) -> Tuple[Any, Any, Any]:
        # Determine provider based on model name
        model_name = self.config.default_model
        provider_name = "openai" # Default
        
        # Simple heuristic mapping
        if "claude" in model_name:
            provider_name = "anthropic"
        elif "gemini" in model_name:
            provider_name = "gemini"
        elif "deepseek" in model_name:
            provider_name = "deepseek"
        elif "llama" in model_name:
            provider_name = "groq"
        elif "kimi" in model_name:
            provider_name = "moonshot"
        elif "qwen" in model_name:
            provider_name = "dashscope"
            
        # Get provider config
        provider_config = getattr(self.config.providers, provider_name, None)
        
        # If not found in presets, check custom
        if not provider_config and provider_name in self.config.providers.custom:
            provider_config = self.config.providers.custom[provider_name]
            
        if not provider_config:
            # Fallback to OpenAI if not found
            logger.warning(f"Provider config for {model_name} not found, falling back to OpenAI defaults")
            provider_config = self.config.providers.openai

        api_key = provider_config.api_key
        base_url = provider_config.api_base
        
        logger.info(f"Initializing model {model_name} with provider {provider_name}")

        if provider_name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            model = ChatAnthropic(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=self.config.agents.defaults.temperature
            )
        elif provider_name == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=self.config.agents.defaults.temperature
            )
        else:
            model = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=self.config.agents.defaults.temperature
            )
        
        # Create agent
        return await AgentFactory.create_for_cli(
            session_id=session_id,
            workspace=self.workspace,
            model=model,
            config=self.config
        )
