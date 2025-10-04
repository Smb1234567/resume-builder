import streamlit as st
from ai_engine import get_ai_response, analyze_student_profile
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
import io
import PyPDF2

# Initialize session state
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

def generate_professional_pdf(title, content, name, email, phone="", doc_type="resume"):
    """Generate beautifully formatted PDF with proper structure"""
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
    
    # Header with name
    story.append(Paragraph(name, title_style))
    contact_text = f"{email}"
    if phone:
        contact_text += f" | {phone}"
    story.append(Paragraph(contact_text, contact_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Parse and format content based on document type
    if doc_type == "ats":
        # Parse ATS resume with proper sections
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers (all caps or starts with **)
            if line.isupper() or (line.startswith('**') and line.endswith('**')):
                current_section = line.replace('**', '').replace(':', '').strip()
                # Add horizontal line
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(f"<b>{current_section}</b>", heading_style))
                story.append(Spacer(1, 0.05*inch))
            
            # Bullet points
            elif line.startswith('-') or line.startswith('•'):
                clean_line = line[1:].strip()
                clean_line = clean_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(f"• {clean_line}", bullet_style))
            
            # Regular content
            else:
                clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if clean_line:
                    story.append(Paragraph(clean_line, content_style))
    
    elif doc_type == "cover":
        # Cover letter format
        story.append(Paragraph("Dear Hiring Manager,", content_style))
        story.append(Spacer(1, 0.15*inch))
        
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_para, content_style))
                story.append(Spacer(1, 0.15*inch))
        
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Sincerely,<br/><b>{name}</b>", content_style))
    
    else:  # human resume
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_para, content_style))
                story.append(Spacer(1, 0.15*inch))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

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

# FILE UPLOAD SECTION
st.header("📤 Step 1: Quick Fill Your Information")

tab_upload, tab_paste = st.tabs(["📁 Upload Resume", "📋 Paste Text"])

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload PDF/TXT to auto-fill",
        type=["pdf", "txt"],
        help="We'll extract your information automatically"
    )

    if uploaded_file:
        with st.spinner("🔍 Analyzing your profile..."):
            try:
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    raw_text = ""
                    for page in pdf_reader.pages:
                        raw_text += page.extract_text()
                else:
                    raw_text = uploaded_file.read().decode('utf-8')
                
                analysis_result = analyze_student_profile(raw_text[:4000])
                
                try:
                    import json
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
                        st.success("✅ Extracted data manually!")
                    except:
                        st.error("❌ Automatic extraction failed. Please use the form below.")
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                print(f"Full error: {e}")

with tab_paste:
    st.info("💡 Paste your info in any of these formats:")
    st.code("""name: John Doe
email: john@example.com
phone: +1234567890
linkedin: linkedin.com/in/johndoe
linkedin_URL: linkedin.com/in/johndoe
github: github.com/johndoe
github_URL: github.com/johndoe
education: B.Tech CS, MIT, 2025
skills: Python, JavaScript, Linux
projects: Built X using Y, Created Z with A
target_job_description: Software Engineer with Python
company: Google
position: Software Engineer""", language="text")
    
    pasted_text = st.text_area(
        "Paste your information here:",
        height=200,
        placeholder="name:Your Name\nemail:your@email.com\n(spaces after colon are optional)"
    )
    
    if st.button("🔍 Parse Pasted Text", use_container_width=True):
        if pasted_text:
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
                        print(f"[PARSE] LinkedIn found: '{value}'")
                    elif key in ["github", "github_url", "github_profile"]:
                        data["github"] = value
                        print(f"[PARSE] GitHub found: '{value}'")
                    elif key in ["education", "degree", "qualification"]:
                        data["education"] = [value]
                    elif key in ["skills", "skill", "technical_skills"]:
                        # Handle both comma-separated and individual items
                        if ',' in value:
                            data["skills"] = [s.strip() for s in value.split(',') if s.strip()]
                        else:
                            data["skills"] = [value]
                    elif key in ["projects", "project", "work", "experience"]:
                        # Handle multiple projects separated by commas
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
                
                # Force form refresh
                st.info("👇 Scroll down to see the form auto-filled with your data!")
        else:
            st.warning("Please paste some text first!")

# Remove the old upload section since we moved it to tabs

# MAIN INPUT FORM
st.header("📝 Step 2: Your Information")

# Show current data status
if st.session_state.student_data:
    if st.session_state.student_data.get('name'):
        with st.expander("📊 Current Loaded Data", expanded=False):
            st.json(st.session_state.student_data)
        st.success(f"✓ Data loaded for: **{st.session_state.student_data.get('name')}**")
        
        # Add refresh button if data exists but form might not show it
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
    
    submitted = st.form_submit_button("🚀 Generate Selected Documents", use_container_width=True)

# GENERATION LOGIC
if submitted and name and email and phone and raw_skills and job_desc:
    
    if not any([gen_ats, gen_human, gen_cover, gen_portfolio]):
        st.error("⚠️ Please select at least one document type to generate!")
    else:
        print("\n" + "="*60)
        print(f"🚀 GENERATION STARTED - Selected: ATS={gen_ats}, Human={gen_human}, Cover={gen_cover}, Portfolio={gen_portfolio}")
        print("="*60)
        
        with st.spinner("🎨 Crafting your professional documents..."):
            
            # 1. ATS RESUME
            if gen_ats:
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
                st.session_state.ats_resume = get_ai_response(ats_prompt, version="ats")
                print(f"✅ ATS Resume: {len(st.session_state.ats_resume)} chars\n")
            
            # 2. HUMAN-FRIENDLY RESUME
            if gen_human:
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
                st.session_state.human_resume = get_ai_response(human_prompt, version="human")
                print(f"✅ Human Resume: {len(st.session_state.human_resume)} chars\n")
            
            # 3. COVER LETTER
            if gen_cover:
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
                st.session_state.cover_letter = get_ai_response(cover_prompt, version="cover_letter")
                print(f"✅ Cover Letter: {len(st.session_state.cover_letter)} chars\n")
            
            # 4. PORTFOLIO WEBSITE
            if gen_portfolio:
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
                st.session_state.portfolio_html = get_ai_response(portfolio_prompt, version="portfolio")
                print(f"✅ Portfolio: {len(st.session_state.portfolio_html)} chars\n")
            
            print("="*60)
            print("✅ ALL SELECTED DOCUMENTS GENERATED!")
            print("="*60 + "\n")

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
                # PDF Download
                ats_pdf = generate_professional_pdf(
                    "Resume", 
                    st.session_state.ats_resume, 
                    name, 
                    email, 
                    phone,
                    doc_type="ats"
                )
                st.download_button(
                    "⬇️ Download as PDF",
                    data=ats_pdf,
                    file_name=f"{name.replace(' ', '_')}_ATS_Resume.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_dl2:
                # TXT Download
                st.download_button(
                    "⬇️ Download as TXT",
                    data=st.session_state.ats_resume,
                    file_name=f"{name.replace(' ', '_')}_ATS_Resume.txt",
                    mime="text/plain",
                    use_container_width=True
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
                human_pdf = generate_professional_pdf(
                    "Resume", 
                    st.session_state.human_resume, 
                    name, 
                    email, 
                    phone,
                    doc_type="human"
                )
                st.download_button(
                    "⬇️ Download as PDF",
                    data=human_pdf,
                    file_name=f"{name.replace(' ', '_')}_Human_Resume.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_dl2:
                st.download_button(
                    "⬇️ Download as TXT",
                    data=st.session_state.human_resume,
                    file_name=f"{name.replace(' ', '_')}_Human_Resume.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        tab_idx += 1
    
    # COVER LETTER TAB
    if st.session_state.cover_letter:
        with tabs[tab_idx]:
            st.subheader("✉️ Personalized Cover Letter")
            if company_name and position:
                st.info(f"✓ Tailored for {position} at {company_name}")
            
            cover_display = f"""
**{name}**  
{email} | {phone}  
{linkedin if linkedin else ''}

---

Dear Hiring Manager,

{st.session_state.cover_letter}

Sincerely,  
{name}
            """
            st.markdown(cover_display)
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                cover_pdf = generate_professional_pdf(
                    "Cover Letter", 
                    st.session_state.cover_letter, 
                    name, 
                    email, 
                    phone,
                    doc_type="cover"
                )
                st.download_button(
                    "⬇️ Download as PDF",
                    data=cover_pdf,
                    file_name=f"{name.replace(' ', '_')}_Cover_Letter.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_dl2:
                cover_full = f"{name}\n{email} | {phone}\n\nDear Hiring Manager,\n\n{st.session_state.cover_letter}\n\nSincerely,\n{name}"
                st.download_button(
                    "⬇️ Download as TXT",
                    data=cover_full,
                    file_name=f"{name.replace(' ', '_')}_Cover_Letter.txt",
                    mime="text/plain",
                    use_container_width=True
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
                file_name=f"{name.replace(' ', '_')}_Portfolio.html",
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
    """)
with col2:
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Use specific metrics
    - Include real projects
    - Customize for each job
    - Proofread before sending
    """)
with col3:
    st.markdown("### ⏱️ Generation Time")
    st.markdown("""
    - ATS Resume: ~15 sec
    - Human Resume: ~15 sec
    - Cover Letter: ~15 sec
    - Portfolio: ~45 sec
    """)

st.caption("💼 Built with ❤️ for students | Powered by OpenRouter AI")
