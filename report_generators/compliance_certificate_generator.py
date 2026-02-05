"""Compliance certificate generator for executive sign-off."""

from typing import Optional
from logging import getLogger
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from core.models import AcquisitionAuditResult
from report_generators.base_report_generator import BaseReportGenerator

logger = getLogger(__name__)


class ComplianceCertificateGenerator(BaseReportGenerator):
    """Generate compliance certificates for acquisition audits.
    
    Professional certificate suitable for:
    - Executive sign-off
    - Board presentations
    - Due diligence documentation
    - Stakeholder communication
    """

    def __init__(self,
                 audit_result: AcquisitionAuditResult,
                 signatory_name: str = "GitRate Auditor",
                 signatory_title: str = "Chief Audit Officer",
                 company_name: str = "GitRate",
                 validity_days: int = 90):
        """Initialize certificate generator.
        
        Args:
            audit_result: Complete audit result
            signatory_name: Name of signing official
            signatory_title: Title of signing official
            company_name: Organization name
            validity_days: Certificate validity period
        """
        super().__init__(audit_result, company_name)
        self.signatory_name = signatory_name
        self.signatory_title = signatory_title
        self.validity_days = validity_days
        self.issued_date = datetime.utcnow()
        self.expiry_date = self.issued_date + timedelta(days=validity_days)
        
        self.page_size = landscape(letter)
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Setup custom styles for certificate."""
        self.styles.add(ParagraphStyle(
            name='CertTitle',
            fontSize=36,
            textColor=colors.HexColor(self.branding_color),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CertSubtitle',
            fontSize=18,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName='Helvetica-BoldOblique',
            spaceAfter=15
        ))
        
        self.styles.add(ParagraphStyle(
            name='CertBody',
            fontSize=12,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            spaceAfter=12,
            leading=14
        ))
        
        self.styles.add(ParagraphStyle(
            name='CertSignature',
            fontSize=11,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=8
        ))

    async def generate(self) -> bytes:
        """Generate compliance certificate.
        
        Returns:
            PDF content as bytes
        """
        self.log_info("Generating compliance certificate")
        
        try:
            buffer = BytesIO()
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.page_size,
                rightMargin=1*inch,
                leftMargin=1*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                title=f"Compliance Certificate - {self.audit_result.repository}",
                author="GitRate",
                subject="Acquisition Audit Compliance Certificate"
            )
            
            story = self._build_certificate()
            
            doc.build(story)
            
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            self.log_info(f"Certificate generated: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            self.log_error(f"Certificate generation failed: {str(e)}")
            raise

    def _build_certificate(self) -> list:
        """Build certificate content."""
        elements = []
        
        # Decorative border (simulated with table)
        border_data = [[""]]
        border_table = Table(border_data, colWidths=[6.5*inch])
        border_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 3, colors.HexColor(self.branding_color)),
        ]))
        elements.append(border_table)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Title
        elements.append(Paragraph("COMPLIANCE CERTIFICATE", self.styles['CertTitle']))
        
        elements.append(Spacer(1, 0.1*inch))
        
        # Subtitle
        elements.append(Paragraph(
            "Acquisition Due Diligence Audit",
            self.styles['CertSubtitle']
        ))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Certificate body
        repo_name = self.audit_result.repository
        score = self.audit_result.scores.overall
        
        body_text = f"""
This is to certify that a comprehensive technical due diligence audit has been 
completed for the repository <b>{repo_name}</b> by {self.company_name}.

<br/><br/>

The audit was conducted in accordance with GitRate's Acquisition Audit Methodology 
and evaluated the following dimensions:

<br/><br/>

<b>Audit Scope:</b><br/>
• IP & Legal Compliance<br/>
• Security & Vulnerability Management<br/>
• Code Quality & Maintainability<br/>
• Team Sustainability & Knowledge Distribution<br/>

<br/>

<b>Overall Assessment Score: {score:.1f}/100</b><br/>

<b>Summary Findings:</b><br/>
• Total Findings: {len(self.audit_result.findings)}<br/>
• Critical Findings: {len(self._get_critical_findings())}<br/>
• High Priority Findings: {len(self._get_high_findings())}<br/>
• Estimated Remediation: {self._calculate_remediation_hours()} hours<br/>

<br/>

<b>Recommendation:</b> {self.audit_result.go_no_go_recommendation}

<br/><br/>

This certificate is valid for {self.validity_days} days from the date of issuance 
and represents the assessment status as of the audit date. Subsequent changes to 
the codebase or infrastructure may affect the validity of these findings.
        """
        
        elements.append(Paragraph(body_text, self.styles['CertBody']))
        
        elements.append(Spacer(1, 0.4*inch))
        
        # Signature section
        elements.append(Paragraph("_" * 50, self.styles['CertSignature']))
        elements.append(Spacer(1, 0.05*inch))
        elements.append(Paragraph(self.signatory_name, self.styles['CertSignature']))
        elements.append(Paragraph(self.signatory_title, self.styles['CertSignature']))
        elements.append(Paragraph(self.company_name, self.styles['CertSignature']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Dates
        issued_str = self.issued_date.strftime("%B %d, %Y")
        expiry_str = self.expiry_date.strftime("%B %d, %Y")
        
        dates_text = f"""
<b>Certificate ID:</b> {self.audit_result.audit_id}<br/>
<b>Issued Date:</b> {issued_str}<br/>
<b>Expiration Date:</b> {expiry_str}
        """
        
        elements.append(Paragraph(dates_text, self.styles['CertBody']))
        
        return elements

    def get_certificate_metadata(self) -> dict:
        """Get metadata about the certificate.
        
        Returns:
            Dict with certificate details
        """
        return {
            "repository": self.audit_result.repository,
            "audit_id": self.audit_result.audit_id,
            "score": self.audit_result.scores.overall,
            "recommendation": self.audit_result.go_no_go_recommendation,
            "issued_date": self.issued_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "signatory": {
                "name": self.signatory_name,
                "title": self.signatory_title,
                "organization": self.company_name,
            },
            "validity_days": self.validity_days,
            "findings_summary": {
                "total": len(self.audit_result.findings),
                "critical": len(self._get_critical_findings()),
                "high": len(self._get_high_findings()),
                "remediation_hours": self._calculate_remediation_hours(),
            }
        }
