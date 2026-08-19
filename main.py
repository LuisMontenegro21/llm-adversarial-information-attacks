import argparse
import os
from dotenv import load_dotenv


load_dotenv()

def check_credentials(model: str) -> str | None:
    OPENAI_KEY = os.getenv('OPENAI_KEY')
    GEMINI_KEY = os.getenv('GEMINI_KEY')
    DEEPSEEK_KEY = os.getenv('DEEPSEEK_KEY')
    if OPENAI_KEY and model == 'openai':
        return OPENAI_KEY
    elif GEMINI_KEY and model == 'gemini':
        return GEMINI_KEY
    elif DEEPSEEK_KEY and model == 'deepseek':
        return DEEPSEEK_KEY
    else:
        raise Exception("No model provider given or no valid provider incerted")
        

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", '-a', type=str, default="web", help="Agent to test")
    parser.add_argument("--model", "-m", type=str, default="openai", help="LLM Model to select")
    parser.add_argument("--attack", '-at', type=str, default="agentpoison", help="Attack to test: agentpoison")
    parser.add_argument("--memory", "-me", type=str, default="mem0", help="Type of memory extraction")