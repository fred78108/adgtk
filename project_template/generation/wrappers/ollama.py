"""Ollama wrapper for the generating content."""

import logging
import requests
from generation.base import Generator
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,)


class OllamaWrapper(Generator):
    """Provides a wrapper to Ollama."""

    description = "a Wrapper for Ollama."
    blueprint: FactoryBlueprint = FactoryBlueprint(
        group_label='generator',
        type_label="ollama",
        arguments={
            "url": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                help_str="The base URL to the Ollama service.",
                default_value="http://localhost:11434"),
            "model": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                help_str="The model to use.",
                default_value="llama3.1"),
        })

    def __init__(self, url: str, model: str):
        self.model = model
        self.base_url = url
        self.completion_url = f"{self.base_url}/v1/completions"
        self.headers = {"Content-Type": "application/json"}
        self.max_tokens = 200

    def generate(self, prompt: str) -> str:
        """Generate a completion using the prompt.

        :param prompt: The prompt to be used.
        :type prompt: str
        :return: The results from Ollama.
        :rtype: str
        """
        data = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": self.max_tokens}
        try:
            response = requests.post(
                self.completion_url, headers=self.headers, json=data)
            if 'error' in response.json():
                msg = response.json()['error']['message']
                logging.error(msg)
                raise RuntimeError(msg)

            # no error = good response so
            return response.json()["choices"][0]["text"]
        except ConnectionError as e:
            logging.error(f"Connection error: {e}")
            raise ConnectionError from e
