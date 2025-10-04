	import os
import requests
import json
from dotenv import load_dotenv
import sys
from datetime import datetime

load_dotenv()

def log(message, level="INFO"):
    """Print timestamped logs to terminal"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)
    sys.stdout.flush()

def get_ai_response(prompt, version="ats"):
    """
    Get AI response with automatic model fallback using requests library
    Args:
        prompt: What to ask the AI
        version: "ats", "human", "cover_letter", "portfolio", "analyze"
    """
    log(f"🤖 Starting AI request for version: {version}")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        log("❌ OPENROUTER_API_KEY not found in .env file", "ERROR")
        raise ValueError("OPENROUTER_API_KEY not found in .env file")
    
    log(f"✓ API key loaded (length: {len(api_key)} chars)")
    
    # Set temperature based on version
    temp_map = {
        "ats": 0.2,
        "human": 0.4,
        "cover_letter": 0.5,
        "portfolio": 0.6,
        "analyze": 0.3
    }
    temperature = temp_map.get(version, 0.3)
    log(f"🌡️ Temperature set to: {temperature}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "ResuMate Pro",
        "Content-Type": "application/json"
    }
    
    log("📡 Headers prepared")
    
    # PRIMARY MODEL: DeepSeek
    log("🔵 Attempting PRIMARY model: DeepSeek Chat v3.1")
    try:
        data = {
            "model": "deepseek/deepseek-chat-v3.1:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        log(f"📝 Prompt length: {len(prompt)} chars")
        log("📤 Sending request to OpenRouter API...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=90
        )
        
        log(f"📥 Response status: {response.status_code}")
        
        if response.status_code != 200:
            log(f"⚠️ API Error Response: {response.text[:200]}", "WARNING")
        
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        log(f"✅ DeepSeek SUCCESS! Response length: {len(result)} chars")
        return result
    
    # BACKUP MODEL: Grok 4
    except Exception as e:
        log(f"❌ DeepSeek FAILED: {str(e)[:100]}", "ERROR")
        log("🟡 Attempting BACKUP model: Grok 4 Fast")
        try:
            data = {
                "model": "x-ai/grok-4-fast:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            log("📤 Sending request to Grok...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=90
            )
            log(f"📥 Grok response status: {response.status_code}")
            
            if response.status_code != 200:
                log(f"⚠️ Grok Error: {response.text[:200]}", "WARNING")
            
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            log(f"✅ Grok SUCCESS! Response length: {len(result)} chars")
            return result
        
        # FALLBACK MODEL: Qwen
        except Exception as e2:
            log(f"❌ Grok FAILED: {str(e2)[:100]}", "ERROR")
            log("🟠 Attempting FALLBACK model: Qwen 72B")
            try:
                data = {
                    "model": "qwen/qwen2-72b-instruct:free",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
                log("📤 Sending request to Qwen...")
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=90
                )
                log(f"📥 Qwen response status: {response.status_code}")
                
                if response.status_code != 200:
                    log(f"⚠️ Qwen Error: {response.text[:200]}", "WARNING")
                
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"]
                log(f"✅ Qwen SUCCESS! Response length: {len(result)} chars")
                return result
            except Exception as e3:
                log(f"💀 ALL MODELS FAILED!", "CRITICAL")
                log(f"DeepSeek: {str(e)[:50]}", "ERROR")
                log(f"Grok: {str(e2)[:50]}", "ERROR")
                log(f"Qwen: {str(e3)[:50]}", "ERROR")
                raise Exception(f"All AI models failed. Last error: {str(e3)}")


def analyze_student_profile(raw_text):
    """
    Analyze uploaded resume/LinkedIn to extract structured data
    """
    log("📄 Starting profile analysis")
    prompt = f"""
    Extract information from this text into a JSON object.
    
    TEXT:
    {raw_text}
    
    Return ONLY this JSON structure (no extra text):
    {{
        "name": "extract full name",
        "email": "extract email address",
        "phone": "extract phone with country code",
        "linkedin": "extract linkedin URL",
        "github": "extract github URL",
        "education": ["extract degree, university"],
        "skills": ["skill1", "skill2", "skill3"],
        "projects": ["project desc 1", "project desc 2"],
        "target_job": "extract target job or position description",
        "company": "extract company name if mentioned",
        "position": "extract position applying for if mentioned"
    }}
    
    Important:
    - For missing fields, use empty string "" or empty list []
    - Return ONLY the JSON, starting with {{ and ending with }}
    - Do NOT truncate. Include ALL projects and skills found
    - No markdown, no explanations, no code blocks
    - Look for keywords like "company:", "position:", "applying for:", "target company"
    """
    
    result = get_ai_response(prompt, version="analyze")
    log(f"📊 Raw AI response length: {len(result)} chars")
    log(f"📊 First 300 chars: {result[:300]}")
    
    # Clean the response
    cleaned = result.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]
    
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    # Extract JSON object
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        cleaned = cleaned[start_idx:end_idx+1]
    
    log(f"🧹 Cleaned response length: {len(cleaned)} chars")
    log(f"🧹 Last 200 chars: {cleaned[-200:]}")
    log("✅ Profile analysis complete")
    
    return cleaned
