from common.agent_functions import FUNCTION_DEFINITIONS
from common.prompt_templates import DEEPGRAM_PROMPT_TEMPLATE, PROMPT_TEMPLATE
from datetime import datetime
import os
import glob


# Function to read documentation files from the deepgram-docs/fern/docs directory
def read_documentation_files(docs_dir):
    """Read all .mdx files in the specified directory and return their contents as a dictionary."""
    documentation = {}
    if not os.path.exists(docs_dir):
        return documentation

    # Get all .mdx files in the directory
    mdx_files = glob.glob(os.path.join(docs_dir, "*.mdx"))

    for file_path in mdx_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Use the filename without extension as the key
                key = os.path.basename(file_path).replace(".mdx", "")
                documentation[key] = content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return documentation
VOICE = "aura-2-odysseus-en"

# audio settings
USER_AUDIO_SAMPLE_RATE = 48000
USER_AUDIO_SECS_PER_CHUNK = 0.05
USER_AUDIO_SAMPLES_PER_CHUNK = round(USER_AUDIO_SAMPLE_RATE * USER_AUDIO_SECS_PER_CHUNK)

AGENT_AUDIO_SAMPLE_RATE = 24000
AGENT_AUDIO_BYTES_PER_SEC = 2 * AGENT_AUDIO_SAMPLE_RATE

VOICE_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"

AUDIO_SETTINGS = {
    "input": {
        "encoding": "linear16",
        "sample_rate": USER_AUDIO_SAMPLE_RATE,
    },
    "output": {
        "encoding": "linear16",
        "sample_rate": AGENT_AUDIO_SAMPLE_RATE,
        "container": "none",
    },
}

LISTEN_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": "nova-3",
        "utterance_end_ms": 1000,  # Resilient to background noise, detects word gaps
        "interim_results": True,   # Required for UtteranceEnd detection
        "smart_format": True       # Cleaner punctuation
    }
}

THINK_SETTINGS = {
    "provider": {
        "type": "open_ai",
        "model": "gpt-4.1",
        "temperature": 0.7,
    },
    "prompt": PROMPT_TEMPLATE.format(
        current_date=datetime.now().strftime("%A, %B %d, %Y")
    ),
    "functions": FUNCTION_DEFINITIONS,
}

SPEAK_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": VOICE,
    }
}

AGENT_SETTINGS = {
    "language": "en",
    "listen": LISTEN_SETTINGS,
    "think": THINK_SETTINGS,
    "speak": SPEAK_SETTINGS,
    "greeting": ""
}

SETTINGS = {"type": "Settings", "audio": AUDIO_SETTINGS, "agent": AGENT_SETTINGS}


class AgentTemplates:
    def __init__(
        self,
        industry="deepgram",
        voiceModel="aura-2-odysseus-en",
        voiceName="",
        docs_dir="deepgram-docs/fern/docs",
    ):
        self.voiceModel = voiceModel
        if voiceName == "":
            self.voiceName = self.get_voice_name_from_model(self.voiceModel)
        else:
            self.voiceName = voiceName

        self.personality = ""
        self.company = ""
        self.first_message = ""
        self.capabilities = ""

        self.industry = industry

        self.voice_agent_url = VOICE_AGENT_URL
        self.settings = SETTINGS
        self.user_audio_sample_rate = USER_AUDIO_SAMPLE_RATE
        self.user_audio_secs_per_chunk = USER_AUDIO_SECS_PER_CHUNK
        self.user_audio_samples_per_chunk = USER_AUDIO_SAMPLES_PER_CHUNK
        self.agent_audio_sample_rate = AGENT_AUDIO_SAMPLE_RATE
        self.agent_audio_bytes_per_sec = AGENT_AUDIO_BYTES_PER_SEC

        match self.industry:
            case "deepgram":
                self.deepgram()

                # Format documentation for the prompt
                doc_text = ""
                # Read documentation files
                self.documentation = read_documentation_files(docs_dir)

                if self.documentation:
                    doc_text = "Available documentation topics: " + ", ".join(
                        self.documentation.keys()
                    )

                self.prompt = DEEPGRAM_PROMPT_TEMPLATE.format(documentation=doc_text)
            case "joint-chiropractic":
                self.joint_chiropractic()
            case "healthcare":
                self.healthcare()
            case "banking":
                self.banking()
            case "pharmaceuticals":
                self.pharmaceuticals()
            case "retail":
                self.retail()
            case "travel":
                self.travel()

        if self.industry != "deepgram":
            # deepgram has its own specific prompt based on the product documentation
            self.prompt = PROMPT_TEMPLATE.format(
                current_date=datetime.now().strftime("%A, %B %d, %Y")
            )

        if self.industry in ["healthcare", "joint-chiropractic"]:
            self.first_message = "Hi, this is Stacey at The Joint Chiropractic in Gadsden. How can I help you today?"
        else:
            self.first_message = f"Hello! I'm {self.voiceName} from {self.company} customer service. {self.capabilities} How can I help you today?"

        self.settings["agent"]["speak"]["provider"]["model"] = self.voiceModel
        self.settings["agent"]["think"]["prompt"] = self.prompt
        # Set proper greeting for joint-chiropractic
        if self.industry == "joint-chiropractic":
            self.settings["agent"]["greeting"] = "Hello! How may I help you?"
        else:
            self.settings["agent"]["greeting"] = self.first_message

        self.prompt = self.personality + "\n\n" + self.prompt

    def deepgram(self, company="Deepgram"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and professional customer service representative for {self.company}, a Voice API company who provides STT and TTS capabilities via API. Your role is to assist potential customers with general inquiries about Deepgram."
        self.capabilities = "I can help you answer questions about Deepgram."
    def healthcare(self, company="The Joint Chiropractic"):
        self.company = company
        self.personality = f"You are Stacey, the friendly, intelligent voice receptionist for The Joint Chiropractic in Gadsden, Alabama. You are on a live phone call."
        self.capabilities = "I can help you schedule appointments and answer questions about our services."

    def joint_chiropractic(self, company="The Joint Chiropractic"):
        self.company = company
        self.personality = f"You are Stacey, the friendly, intelligent voice receptionist for The Joint Chiropractic in Gadsden, Alabama. You are on a live phone call."
        self.capabilities = "I can help you schedule appointments and answer questions about our services."

    def banking(self, company="SecureBank"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a professional and trustworthy banking representative for {self.company}, a secure financial institution. Your role is to assist customers with general information about their accounts and transactions."
        self.capabilities = "I can help you answer questions about banking."

    def pharmaceuticals(self, company="MedLine"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a professional and trustworthy pharmaceutical representative for {self.company}, a secure pharmaceutical company. Your role is to assist customers with general information about their prescriptions and orders."
        self.capabilities = "I can help you answer questions about pharmaceuticals."

    def retail(self, company="StyleMart"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and attentive retail associate for {self.company}, a trendy clothing and accessories store. Your role is to assist customers with general information about their orders and transactions."
        self.capabilities = "I can help you answer questions about retail."

    def travel(self, company="TravelTech"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and professional customer service representative for {self.company}, a tech-forward travel agency. Your role is to assist customers with general information about their travel plans and orders."
        self.capabilities = "I can help you answer questions about travel."

    @staticmethod
    def get_available_industries():
        """Return a dictionary of available industries with display names"""
        return {
            "joint-chiropractic": "The Joint Chiropractic",
            "healthcare": "Healthcare",
            "deepgram": "Deepgram", 
            "banking": "Banking",
            "pharmaceuticals": "Pharmaceuticals",
            "retail": "Retail",
            "travel": "Travel",
        }

    def get_voice_name_from_model(self, model):
        return (
            model.replace("aura-2-", "").replace("aura-", "").split("-")[0].capitalize()
        )
