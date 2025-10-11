import os
import requests
import json
from dotenv import load_dotenv
import sys
from datetime import datetime
import re

load_dotenv()

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

def estimate_tokens(text):
    """Estimate token count (1 token ≈ 4 characters)"""
    return len(text) // 4

def compress_prompt(prompt, max_tokens=3000):
    """
    Intelligently compress prompts while keeping key information
    """
    estimated_tokens = estimate_tokens(prompt)
    
    if estimated_tokens <= max_tokens:
        log(f"Prompt size OK: {estimated_tokens} tokens", "INFO")
        return prompt
    
    log(f"Compressing prompt from {estimated_tokens} to ~{max_tokens} tokens", "WARNING")
    
    # Compression strategies
    compressed = re.sub(r'\n{3,}', '\n\n', prompt)  # Remove extra newlines
    compressed = re.sub(r' {2,}', ' ', compressed)  # Remove extra spaces
    compressed = re.sub(r'Example:.*?(?=\n[A-Z]|\Z)', '', compressed, flags=re.DOTALL)  # Remove examples
    
    return compressed

def validate_json_response(response_text):
    """
    Robust JSON validation with multiple fallback strategies
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
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json.loads(fixed)
    except:
        log("All JSON parsing strategies failed", "ERROR")
        raise ValueError("Unable to parse JSON from AI response")

def sanitize_text_for_xml(text):
    """Sanitize text for XML/PDF generation"""
    if not text:
        return ""
    
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

def get_ai_response(prompt, version="ats", max_retries=2, concise_mode=False, max_response_tokens=None):
    """
    Get AI response with token optimization and fallback
    
    Args:
        prompt: What to ask the AI
        version: Document type
        max_retries: Retry attempts per model
        concise_mode: If True, generates shorter content
        max_response_tokens: Limit response length (None = unlimited)
    
    Returns:
        tuple: (response_text, tokens_used)
    """
    log(f"Starting AI request for version: {version}", "INFO")
    
    # Compress prompt if needed
    original_prompt_tokens = estimate_tokens(prompt)
    prompt = compress_prompt(prompt)
    compressed_prompt_tokens = estimate_tokens(prompt)
    
    if compressed_prompt_tokens < original_prompt_tokens:
        log(f"Saved {original_prompt_tokens - compressed_prompt_tokens} tokens via compression", "SUCCESS")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        log("OPENROUTER_API_KEY not found in .env file", "CRITICAL")
        raise ValueError("API key missing. Please add OPENROUTER_API_KEY to your .env file")
    
    log(f"API key loaded (length: {len(api_key)} chars)", "SUCCESS")
    
    # Adjust temperature and max tokens based on mode
    temp_map = {
        "ats": 0.2,
        "human": 0.4,
        "cover_letter": 0.5,
        "portfolio": 0.6,
        "analyze": 0.3
    }
    temperature = temp_map.get(version, 0.3)
    
    # Set max tokens based on concise mode
    if max_response_tokens is None:
        if concise_mode:
            max_response_tokens = 1500 if version != "portfolio" else 3000
        else:
            max_response_tokens = 2500 if version != "portfolio" else 5000
    
    log(f"Temperature: {temperature}, Max response tokens: {max_response_tokens}", "INFO")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "ResuMate Pro",
        "Content-Type": "application/json"
    }
    
    # Model configurations
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
                    "temperature": temperature,
                    "max_tokens": max_response_tokens
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
                    log("Rate limit hit (429)", "WARNING")
                    errors.append(f"{model['name']}: Rate limited")
                    break
                
                elif response.status_code == 401:
                    log("Authentication failed (401)", "ERROR")
                    raise ValueError("Invalid API key")
                
                elif response.status_code == 503:
                    log("Service unavailable (503)", "WARNING")
                    errors.append(f"{model['name']}: Service unavailable")
                    continue
                
                elif response.status_code != 200:
                    error_text = response.text[:200]
                    log(f"API Error: {error_text}", "WARNING")
                    errors.append(f"{model['name']}: HTTP {response.status_code}")
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                # Validate response structure
                if "choices" not in result or len(result["choices"]) == 0:
                    log("Invalid response structure", "ERROR")
                    errors.append(f"{model['name']}: Invalid response structure")
                    continue
                
                content = result["choices"][0]["message"]["content"]
                
                # Validate content
                if not content or len(content.strip()) < 50:
                    log(f"Response too short ({len(content)} chars)", "WARNING")
                    errors.append(f"{model['name']}: Response too short")
                    continue
                
                # Calculate tokens used
                response_tokens = estimate_tokens(content)
                total_tokens = compressed_prompt_tokens + response_tokens
                
                log(f"SUCCESS with {model['name']}!", "SUCCESS")
                log(f"Tokens - Prompt: {compressed_prompt_tokens}, Response: {response_tokens}, Total: {total_tokens}", "INFO")
                
                return content, total_tokens
            
            except requests.exceptions.Timeout:
                log(f"Timeout after {model['timeout']}s", "ERROR")
                errors.append(f"{model['name']}: Timeout")
                continue
            
            except requests.exceptions.ConnectionError:
                log("Connection error", "ERROR")
                errors.append(f"{model['name']}: Connection error")
                continue
            
            except Exception as e:
                error_msg = str(e)[:100]
                log(f"Error: {error_msg}", "ERROR")
                errors.append(f"{model['name']}: {error_msg}")
                continue
        
        log(f"{model['name']} failed after {max_retries} retries", "ERROR")
    
    # All models failed
    log("ALL MODELS FAILED!", "CRITICAL")
    raise Exception(
        f"All AI models failed. Errors:\n" + 
        "\n".join(f"  • {err}" for err in errors)
    )

def analyze_student_profile(raw_text, reuse_cache=True):
    """
    Analyze uploaded resume with caching support
    
    Args:
        raw_text: Raw text from file
        reuse_cache: If True, returns cached result if text hasn't changed
    
    Returns:
        tuple: (json_string, tokens_used)
    """
    log("Starting profile analysis", "INFO")
    
    # Validate input
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Input text too short - need at least 50 characters")
    
    # Truncate if too long
    if len(raw_text) > 10000:
        log(f"Input truncated from {len(raw_text)} to 10000 chars", "WARNING")
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
- Ensure valid JSON (no trailing commas, proper quotes)
"""
    
    try:
        result, tokens = get_ai_response(prompt, version="analyze", concise_mode=True, max_response_tokens=1000)
        log(f"Raw AI response length: {len(result)} chars", "INFO")
        
        # Validate and parse JSON
        parsed_data = validate_json_response(result)
        
        # Ensure all expected keys exist
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
        
        for key in default_data:
            if key in parsed_data and parsed_data[key]:
                default_data[key] = parsed_data[key]
        
        log("Profile analysis complete", "SUCCESS")
        return json.dumps(default_data), tokens
        
    except Exception as e:
        log(f"Analysis failed: {str(e)}", "ERROR")
        raise Exception(f"Failed to analyze profile: {str(e)}")

def validate_content_completeness(content, doc_type):
    """Validate AI-generated content quality"""
    if not content or len(content.strip()) < 100:
        return False, "Content too short (minimum 100 characters required)"
    
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
        
        if content.count('-') < 5:
            return False, "ATS resume needs more bullet points"
    
    elif doc_type == "human":
        if content.count('\n\n') < 2:
            return False, "Human resume needs multiple paragraphs"
    
    elif doc_type == "cover":
        if len(content) < 200:
            return False, "Cover letter too short (minimum 200 characters)"
    
    elif doc_type == "portfolio":
        if "<!DOCTYPE" not in content and "<html" not in content:
            return False, "Portfolio must be valid HTML"
    
    return True, ""
