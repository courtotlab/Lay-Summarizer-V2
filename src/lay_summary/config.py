"""
Configuration helpers.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from metapub import PubMedFetcher
from openai import OpenAI
from Bio import Entrez


def load_project_config(config_path="./config.json"):
    """
    Load config.json.

    This is the Python-file version of the notebook code:

        with open("./config.json", "r") as config_file:
            config = json.load(config_file)
    """
    config_path = Path(config_path)

    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    return config


def load_openai_api_key():
    """
    Load OPENAI_API_KEY from the environment or .env file.

    The notebook checks:
        openai_api_key = os.environ.get("OPENAI_API_KEY")

    The only small change here is calling load_dotenv() first,
    so a local .env file works when running run_pipeline.py.
    """
    load_dotenv()

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("API key not found. Set OPENAI_API_KEY in your environment or .env file.")

    print(f"API Key Loaded: ...{openai_api_key[-4:]}")

    os.environ["OPENAI_API_KEY"] = openai_api_key

    return openai_api_key


def setup_openai_client(openai_api_key):
    """
    Create the regular OpenAI client, matching the notebook.
    """
    client = OpenAI(api_key=openai_api_key)
    return client


def setup_pubmed_fetcher(config):
    """
    Create PubMedFetcher and configure Entrez, matching the notebook.
    """
    fetch = PubMedFetcher()

    Entrez.email = config["entrez_email"]
    Entrez.api_key = config["entrez_api_key"]

    print(f"Entrez email set: {Entrez.email}")
    print(f"Entrez API key: {Entrez.api_key[:4]}...")

    return fetch


def print_config_summary(config):
    """
    Print the same configuration summary as the notebook.
    """
    num_of_articles = config["num_of_articles"]
    max_summary_length = config["max_summary_length"]
    min_summary_length = config["min_summary_length"]

    print(
        "Lay Summarizer Configuration: \n"
        f" Number of articles: {num_of_articles} \n"
        f" Maximum word length: {max_summary_length} \n"
        f" Minimum word length: {min_summary_length}"
    )
