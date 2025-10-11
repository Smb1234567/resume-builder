import streamlit as st
from ai_engine import get_ai_response, analyze_student_profile, sanitize_text_for_xml, validate_content_completeness
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
import io
import PyPDF2
import re
import json
import time

# ========================
# INPUT VALIDATION FUNCTIONS
# ========================

def validate_email(email):
    """Validate email format"""
    if not email:
        return False, "Email is required"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    return False, "Invalid email format (example: user@domain.com)"

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return False, "Phone number is required"
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)
    # Should have 10-15 digits, optionally starting with +
    if re.match(r'^\+?\d{10,15}$', cleaned):
        return True, ""
    return False, "Invalid phone format (example: +1 234 567 8900)"

def validate_url(url, platform=""):
    """Validate URL format"""
    if not url:
        return True, ""  # Optional field
    
    # Add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Basic URL validation
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if re.match(pattern, url):
        return True, url
    return False, f"Invalid {platform} URL format"

def validate_required_fields(name, email, phone, education, raw_skills, job_desc):
    """Validate all required fields before generation"""
    errors = []
    
    if not name or len(name.strip()) < 2:
        errors.append("• Name must be at least 2 characters")
    
    valid, msg = validate_email(email)
    if not valid:
        errors.append(f"• {msg}")
    
    valid, msg = validate_phone(phone)
    if not valid:
        errors.append(f"• {msg}")
    
    if not education or len(education.strip()) < 10:
        errors.append("• Education must be at least 10 characters")
    
    if not raw_skills or len(raw_skills.strip()) < 50:
        errors.append("• Skills/Projects must be at least 50 characters")
    
    if not job_desc or len(job_desc.strip()) < 30:
        errors.append("• Job description must be at least 30 characters")
    
    return errors

# ========================
# SESSION STATE INITIALIZATION
# ========================

if 'ats_resume' not in st.session_state:
    st.session_state.ats_resume = None
if 'human_resume' not in st.session_state:
    st.session_state.human_resume = None
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = None
if 'portfolio_html' not in st.session_state:
    st.session_state.portfolio_html = None
if 'student_data' not in st.session_state:
    st.session_state.student_data = {}
if 'ats_pdf' not in st.session_state:
    st.session_state.ats_pdf = None
if 'human_pdf' not in st.session_state:
    st.session_state.human_pdf = None
if 'cover_pdf' not in st.session_state:
    st.session_state.cover_pdf = None
if 'current_name' not in st.session_state:
    st.session_state.current_name = ""
if 'current_email' not in st.session_state:
    st.session_state.current_email = ""
if 'current_phone' not in st.session_state:
    st.session_state.current_phone = ""
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False
if 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = None
if 'paste_processed' not in st.session_state:
    st.session_state.paste_processed = False
if 'generation_in_progress' not in st.session_state:
    st.session_state.generation_in_progress = False

# ========================
# PDF GENERATION FUNCTION
# ========================

def generate_professional_pdf(title, content, name, email, phone="", doc_type="resume"):
    """
    Generate beautifully formatted PDF with proper structure and special character handling
    
    Args:
        title: Document title
        content: Main content text
        name: User's name
        email: User's email
        phone: User's phone (optional)
        doc_type: Type of document (ats, human, cover)
    
    Returns:
        bytes: PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=HexColor('#2c3e50'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#7f8c8d'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#2c3e50'),
        spaceBefore=12,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderColor=HexColor('#3498db'),
        borderWidth=0,
        borderPadding=0,
        leftIndent=0
    )
    
    content_style = ParagraphStyle(
        'Content',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=4
    )
    
    project_title_style = ParagraphStyle(
        'ProjectTitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        leftIndent=20,
        fontName='Helvetica-Bold',
        spaceAfter=2,
        textColor=HexColor('#2c3e50')
    )
    
    # Sanitize name and contact info
    name = sanitize_text_for_xml(name)
    email = sanitize_text_for_xml(email)
    phone = sanitize_text_for_xml(phone)
    
    # Header with name
    story.append(Paragraph(name, title_style))
    contact_text = f"{email}"
    if phone:
        contact_text += f" | {phone}"
    story.append(Paragraph(contact_text, contact_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Parse and format content based on document type
    if doc_type == "ats":
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Sanitize line for XML
            clean_line = sanitize_text_for_xml(line.replace('**', '').replace('*', ''))
            
            # Detect section headers (all caps or starts with **)
            if clean_line.replace('&amp;', '&').isupper() and len(clean_line.split()) <= 3:
                current_section = clean_line
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(f"<b>{current_section}</b>", heading_style))
                story.append(Spacer(1, 0.05*inch))
            
            # Project titles (originally had ** around them)
            elif line.startswith('**') and line.endswith('**'):
                project_name = sanitize_text_for_xml(line.replace('**', ''))
                story.append(Paragraph(f"<b>{project_name}</b>", project_title_style))
            
            # Bullet points
            elif line.startswith('-') or line.startswith('•'):
                bullet_text = clean_line[1:].strip() if clean_line.startswith(('-', '•')) else clean_line
                story.append(Paragraph(f"• {bullet_text}", bullet_style))
            
            # Regular content
            else:
                if clean_line:
                    story.append(Paragraph(clean_line, content_style))
    
    elif doc_type == "cover":
        # Cover letter format
        story.append(Paragraph("Dear Hiring Manager,", content_style))
        story.append(Spacer(1, 0.15*inch))
        
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = sanitize_text_for_xml(para.strip())
                story.append(Paragraph(clean_para, content_style))
                story.append(Spacer(1, 0.15*inch))
        
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Sincerely,<br/><b>{name}</b>", content_style))
    
    else:  # human resume
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = sanitize_text_for_xml(para.strip())
                story.append(Paragraph(clean_para, content_style))
                story.append(Spacer(1, 0.15*inch))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {str(e)}")
        raise Exception(f"PDF generation failed: {str(e)}")

# ========================
# STREAMLIT UI
# ========================

st.set_page_config(
    page_title="ResuMate Pro - AI Career Builder",
    page_icon="🚀",
    layout="wide"
)

# HEADER
st.markdown("""
<div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem;">
    <h1>🚀 ResuMate Pro: AI Career Builder</h1>
    <p style="font-size: 1.2em; margin-top: 1rem;">Generate Professional Documents in Minutes</p>
</div>
""", unsafe_allow_html=True)

# Add example data button at the top
col_example, col_clear = st.columns([3, 1])
with col_example:
    if st.button("📝 Load Example Data (Quick Demo)", use_container_width=True):
        st.session_state.student_data = {
            "name": "Alex Johnson",
            "email": "alex.johnson@email.com",
            "phone": "+1 555 123 4567",
            "linkedin": "linkedin.com/in/alexjohnson",
            "github": "github.com/alexjohnson",
            "education": ["B.Tech Computer Science, MIT University (2021-2025), GPA: 8.5/10"],
            "skills": ["Python", "JavaScript", "React", "Node.js", "MongoDB", "Docker", "AWS"],
            "projects": [
                "Built a full-stack e-commerce platform using MERN stack, handling 1000+ daily users",
                "Developed ML sentiment analysis model achieving 92% accuracy on product reviews",
                "Created automated CI/CD pipeline reducing deployment time by 60%"
            ],
            "target_job": "Software Engineer position requiring full-stack development skills in Python, JavaScript, React, and cloud technologies. Strong problem-solving and teamwork abilities essential.",
            "company": "Tech Innovations Inc",
            "position": "Junior Software Engineer"
        }
        st.success("✅ Example data loaded! Scroll down to see the form.")
        st.rerun()

with col_clear:
    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state.student_data = {}
        st.session_state.file_processed = False
        st.session_state.last_uploaded_file = None
        st.session_state.paste_processed = False
        st.session_state.ats_resume = None
        st.session_state.human_resume = None
        st.session_state.cover_letter = None
        st.session_state.portfolio_html = None
        st.session_state.ats_pdf = None
        st.session_state.human_pdf = None
        st.session_state.cover_pdf = None
        st.rerun()

# FILE UPLOAD SECTION
st.header("📤 Step 1: Quick Fill Your Information")

tab_upload, tab_paste = st.tabs(["📁 Upload Resume", "📋 Paste Text"])

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload PDF/TXT to auto-fill",
        type=["pdf", "txt"],
        help="We'll extract your information automatically",
        key="file_uploader"
    )

    # Only process if it's a NEW file
    if uploaded_file and (not st.session_state.file_processed or st.session_state.last_uploaded_file != uploaded_file.name):
        with st.spinner("🔍 Analyzing your profile..."):
            try:
                raw_text = ""
                
                # Read file with proper error handling
                if uploaded_file.type == "application/pdf":
                    try:
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        
                        # Check if PDF is encrypted
                        if pdf_reader.is_encrypted:
                            st.error("❌ This PDF is password-protected. Please upload an unprotected version.")
                            st.stop()
                        
                        # Extract text from all pages
                        for page_num, page in enumerate(pdf_reader.pages):
                            try:
                                text = page.extract_text()
                                if text:
                                    raw_text += text + "\n"
                            except Exception as page_error:
                                print(f"[WARNING] Could not extract text from page {page_num + 1}: {str(page_error)}")
                        
                        # Check if we got any text
                        if not raw_text or len(raw_text.strip()) < 50:
                            st.error("❌ Could not extract text from PDF. This might be a scanned document (image-based). Please upload a text-based PDF or use copy-paste instead.")
                            st.stop()
                        
                    except Exception as pdf_error:
                        st.error(f"❌ Error reading PDF: {str(pdf_error)}")
                        st.info("💡 Try: 1) Use copy-paste instead, 2) Convert PDF to TXT, 3) Ensure PDF is not corrupted")
                        st.stop()
                
                else:  # TXT file
                    try:
                        raw_text = uploaded_file.read().decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            uploaded_file.seek(0)
                            raw_text = uploaded_file.read().decode('latin-1')
                            st.warning("⚠️ File encoding detected as Latin-1. Some characters may not display correctly.")
                        except Exception as txt_error:
                            st.error(f"❌ Error reading text file: {str(txt_error)}")
                            st.stop()
                
                # Analyze the extracted text
                analysis_result = analyze_student_profile(raw_text[:10000])
                
                try:
                    parsed_data = json.loads(analysis_result)
                    
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
                    
                    # Merge parsed data with defaults
                    for key in default_data:
                        if key in parsed_data:
                            default_data[key] = parsed_data[key]
                    
                    st.session_state.student_data = default_data
                    st.session_state.file_processed = True
                    st.session_state.last_uploaded_file = uploaded_file.name
                    
                    st.success("✅ Profile analyzed successfully!")
                    with st.expander("📋 Extracted Information"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Personal:**")
                            st.write(f"Name: {default_data.get('name', 'Not found')}")
                            st.write(f"Email: {default_data.get('email', 'Not found')}")
                            st.write(f"Phone: {default_data.get('phone', 'Not found')}")
                            st.write(f"LinkedIn: {default_data.get('linkedin', 'Not found')}")
                            st.write(f"GitHub: {default_data.get('github', 'Not found')}")
                        with col2:
                            st.write("**Professional:**")
                            st.write(f"Education: {default_data.get('education', [])}")
                            st.write(f"Skills: {default_data.get('skills', [])[:3]}...")
                            st.write(f"Projects: {len(default_data.get('projects', []))} found")
                            st.write(f"Target Job: {default_data.get('target_job', 'Not found')}")
                            st.write(f"Company: {default_data.get('company', 'Not found')}")
                            st.write(f"Position: {default_data.get('position', 'Not found')}")
                        
                except json.JSONDecodeError as je:
                    st.warning("⚠️ Could not parse JSON, attempting manual extraction...")
                    print(f"JSON Error: {je}")
                    print(f"Raw response: {analysis_result}")
                    
                    try:
                        clean_text = analysis_result.replace('```json', '').replace('```', '').strip()
                        parsed_data = json.loads(clean_text)
                        st.session_state.student_data = parsed_data
                        st.session_state.file_processed = True
                        st.session_state.last_uploaded_file = uploaded_file.name
                        st.success("✅ Extracted data manually!")
                    except:
                        st.error("❌ Automatic extraction failed. Please use the form below.")
                    
            except Exception as e:
                st.error(f"❌ Error analyzing file: {str(e)}")
                st.info("💡 Please fill the form manually below")
                print(f"Full error: {e}")
    
    elif uploaded_file and st.session_state.file_processed:
        st.info(f"✓ File '{uploaded_file.name}' already processed. Upload a different file or use 'Clear' button below.")
        if st.button("🗑️ Clear and Re-upload", key="clear_upload"):
            st.session_state.file_processed = False
            st.session_state.last_uploaded_file = None
            st.rerun()

with tab_paste:
    st.info("💡 Paste your info in any of these formats:")
    st.code("""name: John Doe
email: john@example.com
phone: +1234567890
linkedin: linkedin.com/in/johndoe
github: github.com/johndoe
education: B.Tech CS, MIT, 2025
skills: Python, JavaScript, Linux
projects: Built X using Y, Created Z with A
target_job_description: Software Engineer with Python
company: Google
position: Software Engineer""", language="text")
    
    pasted_text = st.text_area(
        "Paste your information here:",
        height=200,
        placeholder="name:Your Name\nemail:your@email.com\n(spaces after colon are optional)",
        key="paste_input"
    )
    
    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        parse_clicked = st.button("🔍 Parse Pasted Text", use_container_width=True, key="parse_btn")
    
    with col_btn2:
        if st.session_state.paste_processed:
            if st.button("🗑️ Clear Parsed Data", use_container_width=True, key="clear_paste"):
                st.session_state.paste_processed = False
                st.rerun()
    
    if parse_clicked and pasted_text:
        with st.spinner("Parsing..."):
            # Enhanced parser for key:value format
            data = {
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
            
            for line in pasted_text.split('\n'):
                if ':' not in line:
                    continue
                
                # Split only on first colon
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                    
                key = parts[0].strip().lower().replace(' ', '_').replace('-', '_')
                value = parts[1].strip()
                
                if not value:
                    continue
                
                # Map all possible key variations
                if key in ["name", "full_name", "fullname"]:
                    data["name"] = value
                elif key in ["email", "email_address", "mail"]:
                    data["email"] = value
                elif key in ["phone", "phone_number", "mobile", "contact"]:
                    data["phone"] = value
                elif key in ["linkedin", "linkedin_url", "linkedin_profile"]:
                    data["linkedin"] = value
                elif key in ["github", "github_url", "github_profile"]:
                    data["github"] = value
                elif key in ["education", "degree", "qualification"]:
                    data["education"] = [value]
                elif key in ["skills", "skill", "technical_skills"]:
                    if ',' in value:
                        data["skills"] = [s.strip() for s in value.split(',') if s.strip()]
                    else:
                        data["skills"] = [value]
                elif key in ["projects", "project", "work", "experience"]:
                    if ',' in value:
                        data["projects"] = [p.strip() for p in value.split(',') if p.strip()]
                    else:
                        data["projects"] = [value]
                elif key in ["target_job_description", "target_job", "job_description", "job", "role"]:
                    data["target_job"] = value
                elif key in ["company", "organization", "company_name"]:
                    data["company"] = value
                elif key in ["position", "position_applying_for", "job_title"]:
                    data["position"] = value
            
            st.session_state.student_data = data
            st.session_state.paste_processed = True
            st.success("✅ Data parsed successfully!")
            
            # Show what was parsed
            with st.expander("📋 Parsed Data - Click to verify"):
                col_show1, col_show2 = st.columns(2)
                with col_show1:
                    st.write("**Personal Info:**")
                    st.write(f"Name: {data['name']}")
                    st.write(f"Email: {data['email']}")
                    st.write(f"Phone: {data['phone']}")
                    st.write(f"LinkedIn: {data['linkedin']}")
                    st.write(f"GitHub: {data['github']}")
                with col_show2:
                    st.write("**Professional Info:**")
                    st.write(f"Education: {data['education']}")
                    st.write(f"Skills ({len(data['skills'])}): {', '.join(data['skills'][:3])}...")
                    st.write(f"Projects ({len(data['projects'])})")
                    st.write(f"Target Job: {data['target_job'][:50]}...")
                    st.write(f"Company: {data['company']}")
                    st.write(f"Position: {data['position']}")
            
            st.info("👇 Scroll down to see the form auto-filled with your data!")
            st.rerun()
    elif parse_clicked and not pasted_text:
        st.warning("Please paste some text first!")

# MAIN INPUT FORM
st.header("📝 Step 2: Your Information")

# Show current data status
if st.session_state.student_data:
    if st.session_state.student_data.get('name'):
        with st.expander("📊 Current Loaded Data", expanded=False):
            st.json(st.session_state.student_data)
        st.success(f"✓ Data loaded for: **{st.session_state.student_data.get('name')}**")
        
        if st.button("🔄 Force Refresh Form", help="Click if form fields are empty"):
            st.rerun()

with st.form("resume_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input(
            "Full Name *",
            value=st.session_state.student_data.get('name', ''),
            placeholder="John Doe"
        )
        email = st.text_input(
            "Email *",
            value=st.session_state.student_data.get('email', ''),
            placeholder="john@example.com"
        )
        phone = st.text_input(
            "Phone *",
            value=st.session_state.student_data.get('phone', ''),
            placeholder="+1 234 567 8900"
        )
        linkedin = st.text_input(
            "LinkedIn URL",
            value=st.session_state.student_data.get('linkedin', ''),
            placeholder="linkedin.com/in/johndoe"
        )
        github = st.text_input(
            "GitHub URL",
            value=st.session_state.student_data.get('github', ''),
            placeholder="github.com/johndoe"
        )
    
    with col2:
        education = st.text_area(
            "Education *",
            value='\n'.join(st.session_state.student_data.get('education', [])),
            placeholder="B.Tech Computer Science, XYZ University (2021-2025)\nGPA: 8.5/10",
            height=120
        )
        
    raw_skills = st.text_area(
        "Your Skills & Projects *",
        value='\n'.join(st.session_state.student_data.get('projects', [])),
        height=150,
        placeholder="Example:\n- Built campus event management app using React & Firebase\n- Developed ML model for sentiment analysis (92% accuracy)\n- Led 5-person team in hackathon (won 2nd place)"
    )
    
    job_desc = st.text_area(
        "Target Job Description *",
        value=st.session_state.student_data.get('target_job', ''),
        height=120,
        placeholder="Seeking Software Engineer with Python, React, and REST API experience. Must have strong problem-solving skills and agile methodology knowledge."
    )
    
    company_name = st.text_input(
        "Company Name (for cover letter)",
        value=st.session_state.student_data.get('company', ''),
        placeholder="Google"
    )
    
    position = st.text_input(
        "Position Applying For (for cover letter)",
        value=st.session_state.student_data.get('position', ''),
        placeholder="Software Engineer Intern"
    )
    
    st.markdown("---")
    st.subheader("🎯 Step 3: Choose What to Generate")
    
    col_select1, col_select2, col_select3, col_select4 = st.columns(4)
    
    with col_select1:
        gen_ats = st.checkbox("📄 ATS Resume", value=True, help="Keyword-optimized for job portals")
    with col_select2:
        gen_human = st.checkbox("❤️ Human Resume", value=True, help="Story-driven for networking")
    with col_select3:
        gen_cover = st.checkbox("✉️ Cover Letter", value=False, help="Personalized application letter")
    with col_select4:
        gen_portfolio = st.checkbox("🌐 Portfolio Website", value=False, help="Professional HTML website")
    
    # Disable button if generation is in progress
    submitted = st.form_submit_button(
        "🚀 Generate Selected Documents", 
        use_container_width=True,
        disabled=st.session_state.generation_in_progress
    )

# GENERATION LOGIC
if submitted and not st.session_state.generation_in_progress:
    
    # Validate required fields
    validation_errors = validate_required_fields(name, email, phone, education, raw_skills, job_desc)
    
    if validation_errors:
        st.error("❌ Please fix the following errors:")
        for error in validation_errors:
            st.error(error)
        st.stop()
    
    # Validate URLs if provided
    if linkedin:
        valid, result = validate_url(linkedin, "LinkedIn")
        if not valid:
            st.error(f"❌ {result}")
            st.stop()
        linkedin = result
    
    if github:
        valid, result = validate_url(github, "GitHub")
        if not valid:
            st.error(f"❌ {result}")
            st.stop()
        github = result
    
    if not any([gen_ats, gen_human, gen_cover, gen_portfolio]):
        st.error("⚠️ Please select at least one document type to generate!")
        st.stop()
    
    # Set generation flag to prevent concurrent requests
    st.session_state.generation_in_progress = True
    
    print("\n" + "="*60)
    print(f"[+] GENERATION STARTED - Selected: ATS={gen_ats}, Human={gen_human}, Cover={gen_cover}, Portfolio={gen_portfolio}")
    print("="*60)
    
    # Calculate total steps for progress tracking
    total_steps = sum([gen_ats, gen_human, gen_cover, gen_portfolio])
    current_step = 0
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. ATS RESUME
        if gen_ats:
            current_step += 1
            progress = current_step / total_steps
            progress_bar.progress(progress)
            status_text.text(f"🔄 Generating ATS Resume... ({current_step}/{total_steps})")
            
            print("\n--- GENERATING: ATS RESUME ---")
            ats_prompt = f"""
Create a professionally formatted ATS-optimized resume for {name}.

PERSONAL INFO:
Email: {email}
Phone: {phone}
LinkedIn: {linkedin}
GitHub: {github}

EDUCATION:
{education}

SKILLS/PROJECTS/EXPERIENCE:
{raw_skills}

TARGET JOB:
{job_desc}

FORMAT REQUIREMENTS (CRITICAL):
1. Use these EXACT section headers in all caps:
   SUMMARY
   SKILLS
   EDUCATION
   PROJECTS
   ACHIEVEMENTS

2. SUMMARY section (3-4 lines):
   - Start with job title the candidate is targeting
   - Include 2-3 most relevant technical skills
   - Mention years of experience or student status

3. SKILLS section:
   - Use bullet points (-)
   - Group by: Programming Languages, Tools & Technologies, Soft Skills
   - Extract EXACT keywords from job description

4. EDUCATION section:
   - Degree name
   - University name
   - Dates (if available)
   - GPA/Grade (if mentioned)

5. PROJECTS section:
   - **Project Name** (bold the title)
   - 2-3 bullet points per project starting with action verbs
   - Include: what you built, technologies used, quantified impact
   - Example: "- Built X using Y, resulting in Z% improvement"

6. ACHIEVEMENTS section (if applicable):
   - Bullet points of key accomplishments
   - Start with action verbs (Developed, Optimized, Led, Implemented)
   - Include numbers/metrics wherever possible

CONTENT RULES:
- Use exact technical keywords from the job description
- Start bullet points with: Developed, Built, Implemented, Optimized, Led, Designed, Created
- Include metrics: "improved by X%", "reduced by Y hours", "increased by Z users"
- NO personal pronouns (I, me, my)
- NO fluff or generic statements
- Keep each bullet to 1-2 lines maximum

OUTPUT: Structured resume content with clear sections. NO explanatory text, NO markdown headers with #.
"""
            try:
                st.session_state.ats_resume = get_ai_response(ats_prompt, version="ats")
                print(f"[+] ATS Resume: {len(st.session_state.ats_resume)} chars")
                
                # Validate content
                is_valid, error_msg = validate_content_completeness(st.session_state.ats_resume, "ats")
                if not is_valid:
                    st.warning(f"⚠️ ATS Resume may be incomplete: {error_msg}")
                    print(f"[!] Validation warning: {error_msg}")
                
                # Generate PDF immediately and store
                print("[i] Generating ATS PDF...")
                st.session_state.ats_pdf = generate_professional_pdf(
                    "Resume", 
                    st.session_state.ats_resume, 
                    name, 
                    email, 
                    phone,
                    doc_type="ats"
                )
                st.session_state.current_name = name
                st.session_state.current_email = email
                st.session_state.current_phone = phone
                print("[+] ATS PDF generated and cached\n")
                
            except Exception as e:
                st.error(f"❌ Failed to generate ATS Resume: {str(e)}")
                print(f"[X] ATS Resume generation failed: {str(e)}")
                st.session_state.ats_resume = None
                st.session_state.ats_pdf = None
        
        # 2. HUMAN-FRIENDLY RESUME
        if gen_human:
            current_step += 1
            progress = current_step / total_steps
            progress_bar.progress(progress)
            status_text.text(f"🔄 Generating Human Resume... ({current_step}/{total_steps})")
            
            print("--- GENERATING: HUMAN RESUME ---")
            human_prompt = f"""
Create a compelling narrative-style resume for {name} that tells their professional story.

BACKGROUND:
{raw_skills}

TARGET JOB:
{job_desc}

REQUIREMENTS:
- Write 3-4 engaging paragraphs (NOT bullet points)
- Paragraph 1: Who you are, your passion, and what drives you
- Paragraph 2: Your most impressive project/achievement with a story
- Paragraph 3: Additional skills and what makes you unique
- Paragraph 4: What you're looking for and what you'll bring to a team

TONE:
- Authentic and passionate (use "I" naturally)
- Show personality without being unprofessional
- Include 1-2 specific examples with details
- Avoid corporate jargon (synergy, leverage, etc.)
- Sound like a real person talking about their work

OUTPUT: 3-4 well-structured paragraphs. NO bullet points, NO section headers.
"""
            try:
                st.session_state.human_resume = get_ai_response(human_prompt, version="human")
                print(f"[+] Human Resume: {len(st.session_state.human_resume)} chars")
                
                # Validate content
                is_valid, error_msg = validate_content_completeness(st.session_state.human_resume, "human")
                if not is_valid:
                    st.warning(f"⚠️ Human Resume may be incomplete: {error_msg}")
                    print(f"[!] Validation warning: {error_msg}")
                
                # Generate PDF immediately and store
                print("[i] Generating Human PDF...")
                st.session_state.human_pdf = generate_professional_pdf(
                    "Resume", 
                    st.session_state.human_resume, 
                    name, 
                    email, 
                    phone,
                    doc_type="human"
                )
                print("[+] Human PDF generated and cached\n")
                
            except Exception as e:
                st.error(f"❌ Failed to generate Human Resume: {str(e)}")
                print(f"[X] Human Resume generation failed: {str(e)}")
                st.session_state.human_resume = None
                st.session_state.human_pdf = None
        
        # 3. COVER LETTER
        if gen_cover:
            current_step += 1
            progress = current_step / total_steps
            progress_bar.progress(progress)
            status_text.text(f"🔄 Generating Cover Letter... ({current_step}/{total_steps})")
            
            # Validate company and position for cover letter
            if not company_name or not position:
                st.warning("⚠️ Company name and position are recommended for cover letter. Using generic version.")
                company_name = company_name or "your organization"
                position = position or "the position"
            
            print("--- GENERATING: COVER LETTER ---")
            cover_prompt = f"""
Write a professional cover letter for {name} applying to {position} at {company_name}.

CANDIDATE BACKGROUND:
{raw_skills}

JOB REQUIREMENTS:
{job_desc}

STRUCTURE (3 paragraphs):

Paragraph 1 (Introduction):
- Express enthusiasm for the specific role at the specific company
- Mention 1 key qualification that makes you perfect for this role
- Show you understand what the company does

Paragraph 2 (Evidence):
- Describe your most relevant project/achievement in detail
- Include specific technologies used
- Include quantified results (improved by X%, built Y that handled Z users)
- Connect it directly to job requirements

Paragraph 3 (Closing):
- Explain what you'll bring to the team
- Express eagerness to contribute
- Thank them and express interest in interview

TONE:
- Professional but personable
- Confident without being arrogant
- Specific, not generic
- 250-300 words total

OUTPUT: 3 paragraphs only. NO "Dear Hiring Manager" (we'll add that). NO signature (we'll add that). Just the body.
"""
            try:
                st.session_state.cover_letter = get_ai_response(cover_prompt, version="cover_letter")
                print(f"[+] Cover Letter: {len(st.session_state.cover_letter)} chars")
                
                # Validate content
                is_valid, error_msg = validate_content_completeness(st.session_state.cover_letter, "cover")
                if not is_valid:
                    st.warning(f"⚠️ Cover Letter may be incomplete: {error_msg}")
                    print(f"[!] Validation warning: {error_msg}")
                
                # Generate PDF immediately and store
                print("[i] Generating Cover Letter PDF...")
                st.session_state.cover_pdf = generate_professional_pdf(
                    "Cover Letter", 
                    st.session_state.cover_letter, 
                    name, 
                    email, 
                    phone,
                    doc_type="cover"
                )
                print("[+] Cover Letter PDF generated and cached\n")
                
            except Exception as e:
                st.error(f"❌ Failed to generate Cover Letter: {str(e)}")
                print(f"[X] Cover Letter generation failed: {str(e)}")
                st.session_state.cover_letter = None
                st.session_state.cover_pdf = None
        
        # 4. PORTFOLIO WEBSITE
        if gen_portfolio:
            current_step += 1
            progress = current_step / total_steps
            progress_bar.progress(progress)
            status_text.text(f"🔄 Generating Portfolio Website... ({current_step}/{total_steps})")
            
            print("--- GENERATING: PORTFOLIO ---")
            portfolio_prompt = f"""
Generate a complete, modern HTML portfolio website for {name}.

PROFILE:
- Name: {name}
- Email: {email}
- Phone: {phone}
- LinkedIn: {linkedin}
- GitHub: {github}
- Education: {education}
- Projects/Skills: {raw_skills}

REQUIREMENTS:
- Modern, responsive single-page design
- Sections: Hero, About, Projects (3-4 project cards), Skills, Contact
- Use gradient backgrounds (purple/blue theme: #6a1b9a, #2196f3)
- Smooth scroll animations
- Mobile-responsive CSS
- Project cards with hover effects
- Tech stack badges for each project
- Working navigation menu
- Contact form (frontend only)
- Self-contained (no external CDN dependencies)

OUTPUT: Complete HTML file starting with <!DOCTYPE html>. NO markdown code blocks, NO explanations.
"""
            try:
                st.session_state.portfolio_html = get_ai_response(portfolio_prompt, version="portfolio")
                print(f"[+] Portfolio: {len(st.session_state.portfolio_html)} chars")
                
                # Validate content
                is_valid, error_msg = validate_content_completeness(st.session_state.portfolio_html, "portfolio")
                if not is_valid:
                    st.warning(f"⚠️ Portfolio may be incomplete: {error_msg}")
                    print(f"[!] Validation warning: {error_msg}")
                
            except Exception as e:
                st.error(f"❌ Failed to generate Portfolio: {str(e)}")
                print(f"[X] Portfolio generation failed: {str(e)}")
                st.session_state.portfolio_html = None
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("✅ All documents generated successfully!")
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        print("="*60)
        print("[+] ALL SELECTED DOCUMENTS GENERATED!")
        print("="*60 + "\n")
        
    except Exception as e:
        st.error(f"❌ Generation failed: {str(e)}")
        print(f"[X] CRITICAL ERROR: {str(e)}")
    
    finally:
        # Reset generation flag
        st.session_state.generation_in_progress = False
        st.rerun()

# RESULTS DISPLAY
if any([st.session_state.ats_resume, st.session_state.human_resume, st.session_state.cover_letter, st.session_state.portfolio_html]):
    
    st.success("✅ Your Documents are Ready!")
    
    # Create tabs dynamically based on what was generated
    tab_names = []
    if st.session_state.ats_resume:
        tab_names.append("📄 ATS Resume")
    if st.session_state.human_resume:
        tab_names.append("❤️ Human Resume")
    if st.session_state.cover_letter:
        tab_names.append("✉️ Cover Letter")
    if st.session_state.portfolio_html:
        tab_names.append("🌐 Portfolio")
    
    tabs = st.tabs(tab_names)
    tab_idx = 0
    
    # ATS RESUME TAB
    if st.session_state.ats_resume:
        with tabs[tab_idx]:
            st.subheader("🤖 ATS-Optimized Resume")
            st.info("✓ Keyword-optimized  ✓ ATS-friendly format  ✓ Quantified achievements")
            
            # Show formatted preview
            st.text_area("Preview", st.session_state.ats_resume, height=400, disabled=True)
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # PDF Download - use cached version
                if st.session_state.ats_pdf:
                    st.download_button(
                        "⬇️ Download as PDF",
                        data=st.session_state.ats_pdf,
                        file_name=f"{st.session_state.current_name.replace(' ', '_')}_ATS_Resume.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="ats_pdf_download"
                    )
                else:
                    st.warning("PDF not generated. Please regenerate documents.")
            
            with col_dl2:
                # TXT Download
                st.download_button(
                    "⬇️ Download as TXT",
                    data=st.session_state.ats_resume,
                    file_name=f"{st.session_state.current_name.replace(' ', '_')}_ATS_Resume.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="ats_txt_download"
                )
        tab_idx += 1
    
    # HUMAN RESUME TAB
    if st.session_state.human_resume:
        with tabs[tab_idx]:
            st.subheader("❤️ Human-Friendly Resume")
            st.info("✓ Story-driven  ✓ Personality showcase  ✓ Networking-ready")
            
            st.markdown(st.session_state.human_resume.replace("\n\n", "\n\n"))
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # PDF Download - use cached version
                if st.session_state.human_pdf:
                    st.download_button(
                        "⬇️ Download as PDF",
                        data=st.session_state.human_pdf,
                        file_name=f"{st.session_state.current_name.replace(' ', '_')}_Human_Resume.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="human_pdf_download"
                    )
                else:
                    st.warning("PDF not generated. Please regenerate documents.")
            
            with col_dl2:
                st.download_button(
                    "⬇️ Download as TXT",
                    data=st.session_state.human_resume,
                    file_name=f"{st.session_state.current_name.replace(' ', '_')}_Human_Resume.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="human_txt_download"
                )
        tab_idx += 1
    
    # COVER LETTER TAB
    if st.session_state.cover_letter:
        with tabs[tab_idx]:
            st.subheader("✉️ Personalized Cover Letter")
            if st.session_state.student_data.get('company') and st.session_state.student_data.get('position'):
                st.info(f"✓ Tailored for {st.session_state.student_data.get('position')} at {st.session_state.student_data.get('company')}")
            
            cover_display = f"""
**{st.session_state.current_name}**  
{st.session_state.current_email} | {st.session_state.current_phone}

---

Dear Hiring Manager,

{st.session_state.cover_letter}

Sincerely,  
{st.session_state.current_name}
            """
            st.markdown(cover_display)
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # PDF Download - use cached version
                if st.session_state.cover_pdf:
                    st.download_button(
                        "⬇️ Download as PDF",
                        data=st.session_state.cover_pdf,
                        file_name=f"{st.session_state.current_name.replace(' ', '_')}_Cover_Letter.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="cover_pdf_download"
                    )
                else:
                    st.warning("PDF not generated. Please regenerate documents.")
            
            with col_dl2:
                cover_full = f"{st.session_state.current_name}\n{st.session_state.current_email} | {st.session_state.current_phone}\n\nDear Hiring Manager,\n\n{st.session_state.cover_letter}\n\nSincerely,\n{st.session_state.current_name}"
                st.download_button(
                    "⬇️ Download as TXT",
                    data=cover_full,
                    file_name=f"{st.session_state.current_name.replace(' ', '_')}_Cover_Letter.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="cover_txt_download"
                )
        tab_idx += 1
    
    # PORTFOLIO TAB
    if st.session_state.portfolio_html:
        with tabs[tab_idx]:
            st.subheader("🌐 Your Professional Portfolio Website")
            st.info("✓ Mobile-responsive  ✓ Modern design  ✓ Ready to host")
            
            # Clean HTML
            portfolio_clean = st.session_state.portfolio_html
            if '```html' in portfolio_clean:
                portfolio_clean = portfolio_clean.split('```html')[1].split('```')[0]
            elif '```' in portfolio_clean:
                portfolio_clean = portfolio_clean.split('```')[1].split('```')[0]
            
            st.components.v1.html(portfolio_clean, height=600, scrolling=True)
            
            st.download_button(
                "⬇️ Download Portfolio HTML",
                data=portfolio_clean,
                file_name=f"{st.session_state.current_name.replace(' ', '_')}_Portfolio.html",
                mime="text/html",
                use_container_width=True
            )
            
            with st.expander("📋 View HTML Source Code"):
                st.code(portfolio_clean, language='html')

# FOOTER
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🎯 Features")
    st.markdown("""
    - ✅ Choose what to generate
    - ✅ Professional PDF formatting
    - ✅ ATS keyword optimization
    - ✅ Story-driven human resumes
    - ✅ Input validation
    - ✅ Error handling
    """)
with col2:
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Use specific metrics
    - Include real projects
    - Customize for each job
    - Proofread before sending
    - Test with example data
    - Check all validations
    """)
with col3:
    st.markdown("### ⏱️ Generation Time")
    st.markdown("""
    - ATS Resume: ~15 sec
    - Human Resume: ~15 sec
    - Cover Letter: ~15 sec
    - Portfolio: ~45 sec
    - Progress tracked live
    """)

st.caption("💼 Built with ❤️ by VISHWANATH SANAPUR FOR EDUNET IBM VIRTUAL INTERNSHIP PROJECT | Powered by OpenRouter AI | Enhanced with Production-Grade Error Handling")
