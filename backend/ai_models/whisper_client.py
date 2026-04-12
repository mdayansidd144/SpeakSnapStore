# STT ke liye 
import os 
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
class WhisperClient:
  def __init__(self):
    self.client= Groq(api_key=os.getenv("GROQ_API_KEY"))
  def transcribe(self,audio_file_path:str)->str:
    """ Convert the audio file to the text"""
    with open  (audio_file_path,"rb") as file:
      transcription = self.client.audio.transcriptions.create(
        file = (audio_file_path,file.read()),
        model = "whisper-large-v3",
        response_format = 'json'
      )  
    return transcription.text  
whisper = WhisperClient()  