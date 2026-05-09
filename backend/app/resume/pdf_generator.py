from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

class PDFGenerator:
    @staticmethod
    def generate_resume_pdf(resume_data: dict) -> BytesIO:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Simple layout
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, resume_data.get("name", "Name Unknown"))
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 70, resume_data.get("email", "Email Unknown"))
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 100, "Professional Summary")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 115, resume_data.get("summary", ""))
        
        # ... Add more fields like Experience, Education
        
        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer
