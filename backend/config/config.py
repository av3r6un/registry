from yaml import safe_load
import os

class Settings:
  SETTING_FP = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'settings.yaml'))
  
  def __init__(self):
    self._load_settings()
  
  def _load_settings(self):
    with open(self.SETTING_FP, 'r', encoding='utf-8') as f:
      data = safe_load(f)
    self.__dict__.update(data)
  
  