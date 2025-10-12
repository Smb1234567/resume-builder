import os
import requests
import json
import streamlit as st
from datetime import datetime
import re
import sys

# ========================
# SECURE API KEY HANDLING
# ========================
def get_api_key():
    """Get API key from secrets or .env"""
    try:
        # Try Streamlit Cloud secrets first
        return st.secrets["openrouter"]["api_key"]
    except Exception:
        # Fallback to .env for local development
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("API key missing. Please add OPENROUTER_API_KEY to your .env file or Streamlit secrets.")
        return api_key

# ========================
# LOGGING FUNCTION
# ========================
def log(message, level="INFO"):
    """Print timestamped logs to terminal - Windows compatible"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    symbols = {
        "INFO": "[i]",
        "ERROR": "[X]",
        "WARNING": "[!]",
        "SUCCESS": "[+]",
        "CRITICAL": "[!!]"
    }
    
    symbol = symbols.get(level, "[i]")
    print(f"[{timestamp}] {symbol} [{level}] {message}", flush=True)
    sys.stdout.flush()

# ========================
# JSON VALIDATION
# ========================
def validate_json_response(response_text):
    """
    Robust JSON validation with multiple fallback strategies
    Handles common AI response issues
    """
    log("Validating JSON response", "INFO")
    
    # Strategy 1: Direct parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        log("Direct JSON parse failed, trying cleanup", "WARNING")
    
    # Strategy 2: Remove markdown code blocks
    cleaned = response_text.strip()
    if '```json' in cleaned:
        cleaned = cleaned.split('```json')[1].split('```')[0]
    elif '```' in cleaned:
        cleaned = cleaned.split('```')[1].split('```')[0]
    
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        log("Markdown cleanup failed, extracting JSON object", "WARNING")
    
    # Strategy 3: Extract JSON object by braces
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        json_str = cleaned[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            log("Brace extraction failed, trying fixes", "WARNING")
    
    # Strategy 4: Fix common JSON issues
    try:
        # Remove trailing commas
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json.loads(fixed)
    except:
        log("All JSON parsing strategies failed", "ERROR")
        raise ValueError("Unable to parse JSON from AI response")

# ========================
# TEXT SANITIZATION
# ========================
def sanitize_text_for_xml(text):
    """
    Sanitize text for XML/PDF generation
    Handles special characters that break ReportLab
    """
    if not text:
        return ""
    
    replacements = {
        '&': '&amp;',
        '<': '<',
        '>': '>',
        '"': '&quot;',
        "'": '&apos;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

# ========================
# AI RESPONSE FUNCTION
# ========================
def get_ai_response(prompt, version="ats", max_retries=2):
    """
    Get AI response with automatic model fallback and retry logic
    
    Args:
        prompt: What to ask the AI
        version: "ats", "human", "cover_letter", "portfolio", "analyze"
        max_retries: Number of retries per model
    
    Returns:
        str: AI generated content
    
    Raises:
        Exception: If all models fail after retries
    """
    log(f"Starting AI request for version: {version}", "INFO")
    
    # Get API key securely
    api_key = get_api_key()
    log(f"API key loaded (length: {len(api_key)} chars)", "SUCCESS")
    
    # Validate prompt length
    prompt_length = len(prompt)
    log(f"Prompt length: {prompt_length} characters", "INFO")
    
    if prompt_length > 50000:
        log("WARNING: Prompt exceeds 50K chars - may hit token limits", "WARNING")
    elif prompt_length > 30000:
        log("Notice: Long prompt detected (30K+ chars)", "INFO")
    
    # Set temperature based on version
    temp_map = {
        "ats": 0.2,
        "human": 0.4,
        "cover_letter": 0.5,
        "portfolio": 0.6,
        "analyze": 0.3
    }
    temperature = temp_map.get(version, 0.3)
    log(f"Temperature set to: {temperature}", "INFO")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "ResuMate Pro",
        "Content-Type": "application/json"
    }
    
    log("Headers prepared", "INFO")
    
    # Model configurations with retry logic
    models = [
        {"name": "DeepSeek Chat v3.1", "id": "deepseek/deepseek-chat-v3.1", "timeout": 120},
        {"name": "Grok 4 Fast", "id": "x-ai/grok-4-fast", "timeout": 90},
        {"name": "Qwen 72B", "id": "qwen/qwen2-72b-instruct", "timeout": 90}
    ]
    
    errors = []
    
    for model in models:
        log(f"Attempting model: {model['name']}", "INFO")
        
        for retry in range(max_retries):
            try:
                if retry > 0:
                    log(f"Retry {retry}/{max_retries} for {model['name']}", "WARNING")
                
                data = {
                    "model": model["id"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
                
                log(f"Sending request to OpenRouter API...", "INFO")
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=model["timeout"]
                )
                
                log(f"Response status: {response.status_code}", "INFO")
                
                # Handle specific HTTP errors
                if response.status_code == 429:
                    log("Rate limit hit (429) - too many requests", "WARNING")
                    errors.append(f"{model['name']}: Rate limited")
                    break  # Don't retry on rate limit, move to next model
                
                elif response.status_code == 401:
                    log("Authentication failed (401) - check API key", "ERROR")
                    raise ValueError("Invalid API key. Please check your OPENROUTER_API_KEY")
                
                elif response.status_code == 503:
                    log("Service unavailable (503) - model may be down", "WARNING")
                    errors.append(f"{model['name']}: Service unavailable")
                    continue  # Retry
                
                elif response.status_code != 200:
                    error_text = response.text[:200]
                    log(f"API Error: {error_text}", "WARNING")
                    errors.append(f"{model['name']}: HTTP {response.status_code}")
                    continue  # Retry
                
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Validate response structure
                if "choices" not in result or len(result["choices"]) == 0:
                    log("Invalid response structure - missing choices", "ERROR")
                    errors.append(f"{model['name']}: Invalid response structure")
                    continue
                
                content = result["choices"][0]["message"]["content"]
                
                # Validate content is not empty
                if not content or len(content.strip()) < 50:
                    log(f"Response too short ({len(content)} chars) - likely incomplete", "WARNING")
                    errors.append(f"{model['name']}: Response too short")
                    continue
                
                log(f"SUCCESS with {model['name']}! Response length: {len(content)} chars", "SUCCESS")
                return content
            
            except requests.exceptions.Timeout:
                log(f"Timeout after {model['timeout']}s", "ERROR")
                errors.append(f"{model['name']}: Timeout")
                continue
            
            except requests.exceptions.ConnectionError:
                log("Connection error - check internet connection", "ERROR")
                errors.append(f"{model['name']}: Connection error")
                continue
            
            except Exception as e:
                error_msg = str(e)[:100]
                log(f"Error: {error_msg}", "ERROR")
                errors.append(f"{model['name']}: {error_msg}")
                continue
        
        # If we get here, all retries for this model failed
        log(f"{model['name']} failed after {max_retries} retries", "ERROR")
    
    # All models failed
    log("ALL MODELS FAILED!", "CRITICAL")
    for error in errors:
        log(f"  - {error}", "ERROR")
    
    raise Exception(
        f"All AI models failed after retries. Errors:\n" + 
        "\n".join(f"  • {err}" for err in errors) +
        "\n\nPlease check:\n1. Internet connection\n2. API key validity\n3. OpenRouter service status"
    )

# ========================
# PROFILE ANALYSIS
# ========================
def analyze_student_profile(raw_text):
    """
    Analyze uploaded resume/LinkedIn to extract structured data
    Enhanced with better validation and error handling
    
    Args:
        raw_text: Raw text from uploaded file
    
    Returns:
        str: JSON string with extracted data
    
    Raises:
        Exception: If analysis fails completely
    """
    log("Starting profile analysis", "INFO")
    
    # Validate input
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Input text too short - need at least 50 characters")
    
    # Truncate if too long (keep first 10K chars for analysis)
    if len(raw_text) > 10000:
        log(f"Input text truncated from {len(raw_text)} to 10000 chars", "WARNING")
        raw_text = raw_text[:10000]
    
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
- Ensure valid JSON (no trailing commas, proper quotes)
"""
    
    try:
        result = get_ai_response(prompt, version="analyze")
        log(f"Raw AI response length: {len(result)} chars", "INFO")
        
        # Validate and parse JSON
        parsed_data = validate_json_response(result)
        
        # Ensure all expected keys exist with defaults
        default_data = {
            "name": "",
            "email": "",
            "phone": "",
            "linkedin": "",
            "github": "",
            "education": [],
            "skills": [],
            "projects": [],
            "target_job": "",
            "company": "",
            "position": ""
        }
        
        # Merge parsed data with defaults
        for key in default_data:
            if key in parsed_data and parsed_data[key]:
                default_data[key] = parsed_data[key]
        
        # Validate critical fields
        if not default_data["name"] and not default_data["email"]:
            log("Warning: No name or email found in profile", "WARNING")
        
        log("Profile analysis complete", "SUCCESS")
        return json.dumps(default_data)
        
    except Exception as e:
        log(f"Analysis failed: {str(e)}", "ERROR")
        raise Exception(f"Failed to analyze profile: {str(e)}")

# ========================
# CONTENT VALIDATION
# ========================
def validate_content_completeness(content, doc_type):
    """
    Validate that AI-generated content is complete and usable
    
    Args:
        content: Generated content string
        doc_type: Type of document (ats, human, cover, portfolio)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not content or len(content.strip()) < 100:
        return False, "Content too short (minimum 100 characters required)"
    
    # Check for common AI failures
    failure_patterns = [
        "I'll help you",
        "I can help",
        "Here's a",
        "I cannot",
        "I apologize",
        "As an AI"
    ]
    
    content_lower = content.lower()[:100]
    for pattern in failure_patterns:
        if pattern.lower() in content_lower:
            return False, f"AI returned explanation instead of content (found: '{pattern}')"
    
    # Document-specific validation
    if doc_type == "ats":
        required_sections = ["SUMMARY", "SKILLS", "EDUCATION", "PROJECTS"]
        missing = [s for s in required_sections if s not in content.upper()]
        if missing:
            return False, f"Missing required sections: {', '.join(missing)}"
        
        if content.count('-') < 5:  # Should have bullet points
            return False, "ATS resume needs more bullet points"
    
    elif doc_type == "human":
        if content.count('\n\n') < 2:  # Should have paragraphs
            return False, "Human resume needs multiple paragraphs"
    
    elif doc_type == "cover":
        if len(content) < 200:
            return False, "Cover letter too short (minimum 200 characters)"
    
    elif doc_type == "portfolio":
        if "<!DOCTYPE" not in content and "<html" not in content:
            return False, "Portfolio must be valid HTML"
    
    return True, ""

