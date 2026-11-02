"""Build small invented PDF headers with the standard library; no originals needed."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ('pdf-ao3-table.pdf', 'pdf-ao3-stacked.pdf', 'pdf-ao3-older-notice.pdf',
         'pdf-ao3-two-series.pdf', 'pdf-browser-unsupported.pdf', 'pdf-no-text.pdf')


def build_pdf(path, stacked=False, older=False, series=False, browser=False, blank=False):
    objects = []
    def obj(data):
        objects.append(data.encode('ascii') if isinstance(data, str) else data)
        return len(objects)
    def literal(value):
        return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    def uri(value):
        return '(' + literal(value) + ')'
    obj('<< /Type /Catalog /Pages 2 0 R >>')
    obj('<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
    obj('')  # page, filled after annotations
    obj('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    commands, annotations = [], []
    title = 'Synthetic PDF ' + ('Stacked' if stacked else 'Older Notice' if older else 'Two Series' if series else 'Table')
    y = 750
    def line(text, x=45, link=None):
        nonlocal y
        commands.append('BT /F1 11 Tf 1 0 0 1 %d %d Tm (%s) Tj ET' % (x, y, literal(text)))
        if link:
            annotations.append(obj('<< /Type /Annot /Subtype /Link /Rect [%d %d %d %d] /Border [0 0 0] /A << /S /URI /URI %s >> >>' % (x, y-3, x+min(500,6*len(text)), y+12, uri(link))))
        y -= 19
    if not blank:
        if browser:
            line('Synthetic saved website: maintenance notice')
            line('Previous work', link='https://archiveofourown.org/works/98000998')
            line('Synthetic browser story'); line('TestWriterPDF')
        else:
            if not older: line(title)
            line('Posted originally on the Archive of Our Own at')
            line('https://archiveofourown.org/works/98000901.', link='https://archiveofourown.org/works/98000901')
            for label, value in [('Rating', 'General Audiences'), ('Categories', 'Gen, F/M'),
                                 ('Fandom', 'Synthetic PDF Fandom'), ('Language', 'English')]:
                if stacked:line(label+':'); line(value,65)
                else:line(label+': '+value)
            if series:line('Series: Part 2 of Synthetic Series, With Comma, Part 3 of Other Synthetic Series')
            line('Stats: Published: 2024-01-02 Updated: 2024-02-03 Words: 1,234 Chapters: 2/?')
            y -= 12; line(title)
            line('by TestWriterPDF', link='https://archiveofourown.org/users/TestAccountPDF/pseuds/TestWriterPDF')
            line('Summary');line('Invented summary for the PDF header test.')
            line('Notes');line('This file contains no original fiction.')
    content='\n'.join(commands).encode('ascii')
    content_id=obj(b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    objects[2]=('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents %d 0 R /Annots [%s] >>' % (content_id,' '.join('%d 0 R'%a for a in annotations))).encode()
    data=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,o in enumerate(objects,1):offsets.append(len(data));data.extend(('%d 0 obj\n'%i).encode()+o+b'\nendobj\n')
    xref=len(data);data.extend(('xref\n0 %d\n0000000000 65535 f \n'%(len(objects)+1)).encode())
    for offset in offsets[1:]:data.extend(('%010d 00000 n \n'%offset).encode())
    data.extend(('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n'%(len(objects)+1,xref)).encode())
    path.write_bytes(data)


def build_all(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for name,opts in zip(NAMES, ({},{'stacked':True},{'older':True},{'series':True},{'browser':True},{'blank':True})):
        build_pdf(folder/name,**opts)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'fixtures')
    build_all(parser.parse_args().output)
