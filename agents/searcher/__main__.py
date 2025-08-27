from asyncio import constants
import json
from json import tool
import logging
import os
import profile
import re
import requests

from services.memory_service import DatabaseMemoryService
import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent_executor import ADKAgentExecutor
from dotenv import load_dotenv
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.tools import google_search
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from instructions import get_agent_information, get_global_instructions
from kanvas import KanvasClient


load_dotenv('/secrets/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def send_email(text_body: str):
    max_retries = 5
    base_delay = 2.0
    sender = os.getenv("MAIL_FROM_ADDRESS")
    username = os.getenv("MAILGUN_SMTP_LOGIN")
    password = os.getenv("MAILGUN_SMTP_PASSWORD")

    if not sender or not username or not password:
        logger.error("Missing required environment variables for email sending.")
        return False

    recipients = os.getenv("RECIPIENTS_EMAIL_ADDRESSES")
    recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]

    smtp_server = "smtp.mailgun.org"
    smtp_port = 587

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ",".join(recipient_list)
    msg["Subject"] = "Prompt Creation Pipeline Results"
    msg.attach(MIMEText(text_body, "plain"))

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt} to send email...")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(sender, recipient_list, msg.as_string())

            logger.info("✅ Email sent successfully via Mailgun SMTP!")
            return True

        except Exception as e:
            wait_time = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Email send attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("❌ All attempts to send email have failed.")

    return False


def main():
    agent_model = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
    agent_info = get_agent_information()
    postgres_memory_service = DatabaseMemoryService("postgresql://" + os.getenv("DB_CONNECTION_STRING"))

    email_sender_agent = LlmAgent(
        name=agent_info["email_sender_agent"]["name"],
        model=agent_model,
        description=agent_info["email_sender_agent"]["description"],
        instruction=agent_info["email_sender_agent"]["instruction"],
        tools=[send_email],
    )

    prompt_poster_agent = LlmAgent(
        name=agent_info["prompt_poster_agent"]["name"],
        model=agent_model,
        description=agent_info["prompt_poster_agent"]["description"],
        instruction=agent_info["prompt_poster_agent"]["instruction"],
        global_instruction=get_global_instructions(),
        tools=[KanvasClient().post_kanvas_message],
        output_key="kanvas_response",
    )

    nugget_poster_agent = LlmAgent(
        name=agent_info["nugget_poster_agent"]["name"],
        model='gemini-2.5-pro',
        description=agent_info["nugget_poster_agent"]["description"],
        instruction=agent_info["nugget_poster_agent"]["instruction"],
        global_instruction=get_global_instructions(),
        tools=[KanvasClient().post_kanvas_nugget_message],
        output_key="nugget_kanvas_response",
    )

    profile_chooser_agent = LlmAgent(
        name=agent_info["profile_chooser_agent"]["name"],
        model=agent_model,
        description=agent_info["profile_chooser_agent"]["description"],
        instruction=agent_info["profile_chooser_agent"]["instruction"],
        global_instruction=get_global_instructions(),
        tools=[KanvasClient().fetch_random_profile],
        output_key="chosen_profile",
    )

    quality_assurance_agent = LlmAgent(
        name=agent_info["quality_assurance_agent"]["name"],
        model='gemini-2.5-pro',
        description=agent_info["quality_assurance_agent"]["description"],
        instruction=agent_info["quality_assurance_agent"]["instruction"],
        tools=[postgres_memory_service.store_quality_result],
    )

    prompt_creation_agent = LlmAgent(
        name=agent_info["prompt_creator_agent"]["name"],
        model="gemini-2.5-pro",
        description=agent_info["prompt_creator_agent"]["description"],
        instruction=agent_info["prompt_creator_agent"]["instruction"],
        global_instruction=get_global_instructions(),
        tools=[KanvasClient().fetch_random_profile],
        output_key="content",
    )
    search_agent = LlmAgent(
        name=agent_info["search_agent"]["name"],
        model=agent_model,
        description=agent_info["search_agent"]["description"],
        instruction=agent_info["search_agent"]["instruction"],
        global_instruction=get_global_instructions(),
        tools=[google_search],
        output_key="trend_result",
    )

    prompt_creation_pipeline_agent = SequentialAgent(
        name="prompt_creation_pipeline_agent",
        description="Executes a pipeline of agents to create prompts from Google trending topics given a category.",
        sub_agents=[
            search_agent,
            profile_chooser_agent,
            prompt_creation_agent,
            quality_assurance_agent,
            prompt_poster_agent,
            nugget_poster_agent,
            email_sender_agent
        ],
    )

    # Agent card (metadata)
    agent_card = AgentCard(
        name=prompt_creation_pipeline_agent.name,
        description=prompt_creation_pipeline_agent.description,
        url=os.getenv("LOCAL_AGENT_ADDRESS", "http://localhost:10002"),
        version="1.0.0",
        defaultInputModes=["text", "text/plain"],
        defaultOutputModes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="call_search_agent",
                name="call_search_agent",
                description="Calls the search agent to get trending topics.",
                tags=["search", "google", "trending", "topics"],
                examples=[
                    "What is trending in technology",
                ],
            ),
            AgentSkill(
                id="call_profile_chooser_agent",
                name="call_profile_chooser_agent",
                description="calls the profile chooser agent to get a random user profile.",
                tags=["profile", "user", "random"],
            ),
            AgentSkill(
                id="call_prompt_creator_agent",
                name="call_prompt_creator_agent",
                description="calls the prompt creator agent that creates a prompt blueprint from the results of the search agent",
                tags=["search", "keywords", "topics"],
            ),
            AgentSkill(
                id="call_quality_assurance_agent",
                name="call_quality_assurance_agent",
                description="calls the quality assurance agent to quality test the prompt blueprint proposed by the prompt_creator_agent",
                tags=["email", "send", "keywords"],
            ),
            AgentSkill(
                id="call_prompt_post_agent",
                name="call_prompt_post_agent",
                description="calls the prompt post agent to post the generated prompt to Kanvas API.",
                tags=["post", "prompt", "kanvas"],
            ),
            AgentSkill(
                id="call_nugget_post_agent",
                name="call_nugget_post_agent",
                description="calls the nugget post agent to post the generated nugget to Kanvas API.",
                tags=["post", "nugget", "kanvas"],
            ),
            AgentSkill(
                id="call_email_sender_agent",
                name="call_email_sender_agent",
                description="calls the email sender agent to send an email with the extracted keywords.",
                tags=["email", "send", "keywords"],
            ),
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=prompt_creation_pipeline_agent,
        ),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    uvicorn.run(
        server.build(),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 10002)),
    )


if __name__ == "__main__":
    main()
