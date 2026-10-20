"""Render the editable defense guide in black SimHei with enclosed tables."""
from pathlib import Path
import re,sys
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'docs/穗游_答辩精细讲解稿.md'
OUT=ROOT/'docs/穗游_答辩精细讲解稿.pdf'
pdfmetrics.registerFont(TTFont('SimHei','C:/Windows/Fonts/simhei.ttf'))
base=dict(fontName='SimHei',textColor=colors.black,wordWrap='CJK')
styles={
 'body':ParagraphStyle('body',fontSize=10.2,leading=16.6,spaceAfter=8,**base),
 'h1':ParagraphStyle('h1',fontSize=23,leading=34,spaceAfter=18,**base),
 'h2':ParagraphStyle('h2',fontSize=17,leading=26,spaceAfter=14,**base),
 'h3':ParagraphStyle('h3',fontSize=11.5,leading=19,spaceBefore=8,spaceAfter=7,keepWithNext=True,**base),
 'cell':ParagraphStyle('cell',fontSize=8.5,leading=13.4,**base),
}
def para(s,style='body'):
 s=re.sub(r'`([^`]+)`',r'\1',s)
 return Paragraph(escape(s),styles[style])
lines=SRC.read_text(encoding='utf-8').splitlines();story=[];i=0
while i<len(lines):
 line=lines[i].strip();i+=1
 if not line:continue
 if line=='<!-- pagebreak -->':story.append(PageBreak());continue
 if line.startswith('|'):
  rows=[line]
  while i<len(lines) and lines[i].strip().startswith('|'):
   rows.append(lines[i].strip());i+=1
  rows=[r for r in rows if not re.fullmatch(r'[\s|:\-]+',r)]
  cells=[[para(c.strip(),'cell') for c in r.strip('|').split('|')] for r in rows]
  n=len(cells[0]); widths={3:[108,178,201],4:[88,129,135,135],2:[125,362]}.get(n,[487/n]*n)
  t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
  t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.5,colors.black),('BOX',(0,0),(-1,-1),.8,colors.black),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
  story.extend([t,Spacer(1,10)]);continue
 level=len(line)-len(line.lstrip('#'))
 if level and line[level:level+1]==' ':story.append(para(line[level+1:],'h'+str(min(level,3))))
 else:story.append(para(line))
def footer(c,doc):
 c.setFillColor(colors.black);c.setStrokeColor(colors.black);c.setFont('SimHei',7.5)
 c.drawString(54,810,'穗游 · 答辩详解 | 1.0-defense')
 c.drawRightString(541,810,'整理：2026.10.20 / 运行证据：2026.10.14')
 c.line(54,46,541,46);c.drawString(54,31,'源码、正式报告与证据对应阅读；历史回放不等于当前实时查询')
 c.drawRightString(541,31,str(doc.page))
doc=SimpleDocTemplate(str(OUT),pagesize=(595.28,841.89),leftMargin=54,rightMargin=54,topMargin=56,bottomMargin=58,title='穗游广州周末出行Agent：答辩精细讲解稿',author='待填写')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
sys.stdout.reconfigure(encoding='utf-8')
print({'pages':len(PdfReader(OUT).pages),'path':str(OUT)})
