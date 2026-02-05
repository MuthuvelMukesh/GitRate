"""PDF report generator for professional acquisition audit reports."""

from typing import List, Dict, Any, Tuple
from logging import getLogger
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from core.models import AcquisitionAuditResult, AuditFinding
from report_generators.base_report_generator import BaseReportGenerator

logger = getLogger(__name__)


class PDFReportGenerator(BaseReportGenerator):
    """Generate professional PDF audit reports.
    
    Sections:
    1. Cover page with executive summary
    2. Audit overview and methodology
    3. Score summary with visualizations
    4. Critical findings
    5. Detailed findings by category
    6. Remediation roadmap
    7. Risk assessment
    8. Appendix
    """

    def __init__(self, 
                 audit_result: AcquisitionAuditResult,
                 company_name: str = "GitRate",
                 include_logo: bool = True,
                 font_name: str = "Helvetica"):
        """Initialize PDF report generator.
        
        Args:
            audit_result: Complete audit result
            company_name: Organization name
            include_logo: Whether to include company logo
            font_name: Font family (Helvetica, Times-Roman, Courier)
        """
        super().__init__(audit_result, company_name)
        self.include_logo = include_logo
        self.font_name = font_name
        self.page_size = letter
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Setup custom paragraph styles."""
        # Title styles
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor(self.branding_color),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=f"{self.font_name}-Bold"
        ))
        
        # Subtitle
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.grey,
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # Critical finding style
        self.styles.add(ParagraphStyle(
            name='CriticalFinding',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.red,
            spaceAfter=8,
            fontName=f"{self.font_name}-Bold"
        ))
        
        # Score metric style
        self.styles.add(ParagraphStyle(
            name='ScoreMetric',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            fontName=f"{self.font_name}-Bold"
        ))

    async def generate(self) -> bytes:
        """Generate PDF report.
        
        Returns:
            PDF content as bytes
        """
        self.log_info("Generating PDF report")
        
        try:
            buffer = BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.page_size,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=1*inch,
                bottomMargin=0.75*inch,
                title=f"GitRate Audit Report - {self.audit_result.repository}",
                author="GitRate",
                subject="Acquisition Audit Report"
            )
            
            # Build story elements
            story = []
            
            # 1. Cover page
            story.extend(self._build_cover_page())
            story.append(PageBreak())
            
            # 2. Executive summary
            story.extend(self._build_executive_summary())
            story.append(PageBreak())
            
            # 3. Score overview
            story.extend(self._build_score_overview())
            story.append(PageBreak())
            
            # 4. Critical findings
            critical = self._get_critical_findings()
            if critical:
                story.extend(self._build_critical_findings_section(critical))
                story.append(PageBreak())
            
            # 5. Detailed findings by category
            categorized = self._categorize_findings()
            story.extend(self._build_findings_sections(categorized))
            story.append(PageBreak())
            
            # 6. Remediation roadmap
            story.extend(self._build_remediation_section())
            story.append(PageBreak())
            
            # 7. Risk assessment
            story.extend(self._build_risk_assessment())
            
            # Build PDF
            doc.build(story)
            
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            self.log_info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            self.log_error(f"PDF generation failed: {str(e)}")
            raise

    def _build_cover_page(self) -> List:
        """Build cover page with title and key metrics."""
        elements = []
        
        # Company name
        elements.append(Spacer(1, 1.5*inch))
        elements.append(Paragraph(
            self.company_name,
            self.styles['Subtitle']
        ))
        
        # Title
        elements.append(Paragraph(
            "Acquisition Audit Report",
            self.styles['CustomTitle']
        ))
        
        # Repository name
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(
            f"Repository: <b>{self.audit_result.repository}</b>",
            self.styles['Normal']
        ))
        
        # Overall score with emphasis
        elements.append(Spacer(1, 0.5*inch))
        score_text = f"Overall Score: <b>{self.audit_result.scores.overall:.1f}/100</b>"
        elements.append(Paragraph(score_text, self.styles['Heading2']))
        
        # Recommendation
        elements.append(Spacer(1, 0.3*inch))
        rec_color = "green" if "GREEN" in self.audit_result.go_no_go_recommendation else \
                   "red" if "RED" in self.audit_result.go_no_go_recommendation else "orange"
        rec_text = f"<font color='{rec_color}'><b>{self.audit_result.go_no_go_recommendation}</b></font>"
        elements.append(Paragraph(rec_text, self.styles['Heading2']))
        
        # Metadata
        elements.append(Spacer(1, 0.8*inch))
        metadata = [
            f"Audit Date: {self.audit_result.audit_date.strftime('%B %d, %Y')}",
            f"Audit Duration: {self.audit_result.audit_duration_seconds / 60:.1f} minutes",
            f"Audit ID: {self.audit_result.audit_id}",
        ]
        for meta in metadata:
            elements.append(Paragraph(meta, self.styles['Normal']))
        
        return elements

    def _build_executive_summary(self) -> List:
        """Build executive summary section."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['Heading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary text
        elements.append(Paragraph(
            self.audit_result.executive_summary,
            self.styles['BodyText']
        ))
        
        # Key metrics
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Key Metrics:", self.styles['Heading3']))
        
        metrics_data = [
            ["Metric", "Value"],
            ["Total Findings", str(len(self.audit_result.findings))],
            ["Critical Findings", str(len(self._get_critical_findings()))],
            ["High Priority Findings", str(len(self._get_high_findings()))],
            ["Estimated Remediation Hours", str(self._calculate_remediation_hours())],
            ["Estimated Remediation Cost", f"${self._calculate_remediation_cost():,.0f}"],
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.branding_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), f'{self.font_name}-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(metrics_table)
        
        # Red flags
        if self.audit_result.red_flags:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("Red Flags:", self.styles['Heading3']))
            
            for flag in self.audit_result.red_flags[:5]:  # Top 5
                elements.append(Paragraph(f"• {flag}", self.styles['Normal']))
        
        return elements

    def _build_score_overview(self) -> List:
        """Build detailed score overview section."""
        elements = []
        
        elements.append(Paragraph("Score Overview", self.styles['Heading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        scores = self.audit_result.scores
        
        # Create score breakdown table
        score_data = [
            ["Category", "Score", "Assessment"],
            ["IP & Legal", f"{scores.ip_legal:.1f}", self._get_score_description(scores.ip_legal)],
            ["Security", f"{scores.security:.1f}", self._get_score_description(scores.security)],
            ["Code Quality", f"{scores.code_quality:.1f}", self._get_score_description(scores.code_quality)],
            ["Team Sustainability", f"{scores.team_sustainability:.1f}", self._get_score_description(scores.team_sustainability)],
            ["OVERALL", f"{scores.overall:.1f}", self._get_score_description(scores.overall)],
        ]
        
        score_table = Table(score_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.branding_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), f'{self.font_name}-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, -1), (-1, -1), f'{self.font_name}-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(self.branding_color)),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(score_table)
        
        return elements

    def _build_critical_findings_section(self, critical: List[AuditFinding]) -> List:
        """Build critical findings section."""
        elements = []
        
        elements.append(Paragraph(f"Critical Findings ({len(critical)})", self.styles['Heading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        for i, finding in enumerate(critical, 1):
            elements.append(Paragraph(
                f"{i}. {finding.title}",
                self.styles['CriticalFinding']
            ))
            
            elements.append(Paragraph(
                f"<b>Category:</b> {finding.category}",
                self.styles['Normal']
            ))
            
            elements.append(Paragraph(
                f"<b>Description:</b> {finding.description}",
                self.styles['Normal']
            ))
            
            elements.append(Paragraph(
                f"<b>Recommendation:</b> {finding.recommendation}",
                self.styles['Normal']
            ))
            
            elements.append(Paragraph(
                f"<b>Estimated Hours:</b> {finding.estimation_hours}",
                self.styles['Normal']
            ))
            
            elements.append(Spacer(1, 0.2*inch))
        
        return elements

    def _build_findings_sections(self, categorized: Dict[str, List[AuditFinding]]) -> List:
        """Build detailed findings sections by category."""
        elements = []
        
        for category, findings in sorted(categorized.items()):
            elements.append(Paragraph(f"{category} ({len(findings)} findings)", self.styles['Heading2']))
            elements.append(Spacer(1, 0.15*inch))
            
            # Create findings table
            finding_data = [
                ["Finding", "Severity", "Hours"],
            ]
            
            for f in findings[:10]:  # Limit to 10 per page
                icon = self._get_severity_icon(f.severity)
                finding_data.append([
                    f.title[:40] + "..." if len(f.title) > 40 else f.title,
                    f"{icon} {f.severity}",
                    str(int(f.estimation_hours))
                ])
            
            findings_table = Table(finding_data, colWidths=[3.5*inch, 1.5*inch, 0.75*inch])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.branding_color)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), f'{self.font_name}-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(findings_table)
            elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _build_remediation_section(self) -> List:
        """Build remediation roadmap section."""
        elements = []
        
        elements.append(Paragraph("Remediation Roadmap", self.styles['Heading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        total_hours = self._calculate_remediation_hours()
        total_cost = self._calculate_remediation_cost()
        
        elements.append(Paragraph(
            f"Total Estimated Effort: <b>{total_hours} hours</b> (${total_cost:,.0f})",
            self.styles['Normal']
        ))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Timeline estimate
        if self.audit_result.roadmap_90_day:
            elements.append(Paragraph("90-Day Roadmap:", self.styles['Heading3']))
            
            for i, task in enumerate(self.audit_result.roadmap_90_day[:5], 1):
                priority = getattr(task, 'priority', 'MEDIUM')
                week = getattr(task, 'week', 1)
                
                elements.append(Paragraph(
                    f"<b>Week {week}:</b> {task.title} [Priority: {priority}]",
                    self.styles['Normal']
                ))
        
        return elements

    def _build_risk_assessment(self) -> List:
        """Build risk assessment section."""
        elements = []
        
        elements.append(Paragraph("Risk Assessment", self.styles['Heading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Overall risk
        overall = self.audit_result.scores.overall
        if overall >= 80:
            risk_level = "LOW"
            risk_color = "green"
        elif overall >= 60:
            risk_level = "MEDIUM"
            risk_color = "orange"
        else:
            risk_level = "HIGH"
            risk_color = "red"
        
        elements.append(Paragraph(
            f"Overall Risk Level: <font color='{risk_color}'><b>{risk_level}</b></font>",
            self.styles['Normal']
        ))
        
        # Recommendation
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(
            f"<b>Acquisition Recommendation:</b> {self.audit_result.go_no_go_recommendation}",
            self.styles['Normal']
        ))
        
        return elements

    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level."""
        icons = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }
        return icons.get(severity, "●")
