"""Rebuild small synthetic fixtures using only stdlib and fixture_cases.json.

No private source files, network access or extractor output is used at build time.
Names, summaries and chapter text are invented. Counts describe test scenarios,
not the length of the placeholder chapter. Run: python3 tests/build_fixtures.py
"""
import datetime
import json
from html import escape as esc
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

HERE = Path(__file__).resolve().parent
OUT = HERE / 'fixtures'
CASES = json.loads((HERE / 'fixture_cases.json').read_text())


def e(value):
    return esc(str(value), quote=True)


def page(body, cls='', head=''):
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Synthetic metadata test</title>'
            + head + '</head><body class="' + cls + '">' + body + '</body></html>')


def ps(text):
    return ''.join('<p>' + e(p) + '</p>' for p in text.split('\n\n'))


def metadata(f, extra='', description=True, authors=True, url=True):
    parts = ['<dc:title>' + e(f['title']) + '</dc:title>']
    if authors:
        parts += ['<dc:creator>' + e(a) + '</dc:creator>' for a in f.get('author', [])]
    parts += ['<dc:language>' + e(f.get('langcode', 'en')) + '</dc:language>']
    if description and f.get('description'):
        parts += ['<dc:description>' + e(f['description']) + '</dc:description>']
    if url and f.get('storyUrl'):
        parts += ['<dc:identifier opf:scheme="url">' + e(f['storyUrl']) + '</dc:identifier>']
    return ''.join(parts) + extra


def package(meta, docs, other_items=''):
    manifest = ''.join('<item id="p%d" href="%s" media-type="application/xhtml+xml"/>' % (i, e(n)) for i,n in enumerate(docs))
    spine = ''.join('<itemref idref="p%d"/>' % i for i in range(len(docs)))
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" xmlns:opf="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0" unique-identifier="synthetic-id">'
            '<metadata><dc:identifier id="synthetic-id">urn:synthetic:metadata-test</dc:identifier>'
            + meta + '</metadata><manifest>' + manifest + other_items + '</manifest><spine>' + spine + '</spine></package>')


def write_epub(path, f, docs, extra='', resources=None, other_items='', opf_meta=None):
    resources = resources or {}
    opf = package(metadata(f, extra) if opf_meta is None else opf_meta, docs, other_items)
    items = {'mimetype':'application/epub+zip', 'META-INF/container.xml':
             '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
             '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
             'content.opf':opf, **docs, **resources}
    with ZipFile(path, 'w') as z:
        for name, value in items.items():
            info = ZipInfo(name, (2020,1,1,0,0,0))
            info.compress_type = ZIP_STORED if name == 'mimetype' else ZIP_DEFLATED
            z.writestr(info, value.encode('utf-8'))


def labels(f):
    mapping = {'fandoms':'Fandom', 'category':'Category','genre':'Genre','ships':'Ships',
               'characters':'Characters','freeformtags':'Additional Tags','ao3categories':'Categories',
               'rating':'Rating','warnings':'Warnings','language':'Language','status':'Status',
               'numChapters':'Chapters','numWords':'Words','datePublished':'Published',
               'dateUpdated':'Updated','dateCreated':'Packaged'}
    result=[]
    for key,label in mapping.items():
        if key not in f:continue
        value=f[key]
        if key=='numChapters':value=f.get('chapterslashtotal',value)
        if key in ('dateCreated','datePublished','dateUpdated'):value=value.replace('T',' ')
        if isinstance(value,list):value=', '.join(value)
        result.append((label,str(value)))
    return result


def titlepage(f, bold=False):
    body='<h3><a href="'+e(f.get('storyUrl','https://example.com/synthetic'))+'">'+e(f['title'])+'</a> by '+e(', '.join(f.get('author',[])))+'</h3>'
    body+=''.join(('<b>'+e(k)+':</b> '+e(v)+'<br/>' if bold else '<p>'+e(k)+': '+e(v)+'</p>') for k,v in labels(f))
    return page(body,'fff_titlepage' if bold else '')


def stats(f, separator=' '):
    fields=[]
    for key,label in [('datePublished','Published'),('dateUpdated','Updated'),('numWords','Words')]:
        if key in f:fields.append(label+': '+str(f[key])[:10] if key.startswith('date') else label+': '+str(f[key]))
    if 'numChapters' in f:fields.append('Chapters: '+f.get('chapterslashtotal',str(f['numChapters'])+'/'+str(f.get('numChaptersTotal','?'))))
    return separator.join(fields)


def ao3_dl(f, nested=False, thin=False):
    mapping={'rating':'Rating','warnings':'Archive Warning','ao3categories':'Category','fandoms':'Fandom','ships':'Relationship','characters':'Characters','freeformtags':'Additional Tags','language':'Language'}
    out='<dl class="tags">'
    for key,label in mapping.items():
        if key in f:
            values=f[key] if isinstance(f[key],list) else [f[key]]
            out+='<dt>'+label+':</dt><dd>'+', '.join('<a href="https://example.com/tag">'+e(v)+'</a>' for v in values)+'</dd>'
    if 'series' in f:
        name,idx=f['series'].rsplit(' [',1)
        out+='<dt>Series:</dt><dd>Part '+idx[:-1]+' of the <a href="'+e(f.get('seriesUrl','https://archiveofourown.org/series/999'))+'">'+e(name)+'</a> Next Work →</dd>'
    stat=stats(f)
    if thin and 'numWords' in f:stat=stat.replace(str(f['numWords']),format(f['numWords'],',').replace(',','\u2009'))
    if nested:
        # No separator between adjacent dt/dd nodes: regression for glued stats.
        stat=''.join('<dt>'+e(k)+':</dt><dd>'+e(v)+'</dd>' for k,v in (p.split(': ',1) for p in stat.replace(' Updated:', '|Updated:').replace(' Words:', '|Words:').replace(' Chapters:', '|Chapters:').replace(' Published:', '|Published:').split('|')))
        stat='<dl class="stats">'+stat+'<dt>Comments:</dt><dd>9</dd></dl>'
    else:stat=e(stat)
    return out+'<dt>Stats:</dt><dd>'+stat+'</dd></dl>'


def authors(f):
    return ', '.join('<a rel="author" href="'+e(url)+'">'+e(name)+'</a>' for name,url in zip(f.get('author',[]),f.get('authorUrl',[]))) or e(', '.join(f.get('author',[])))


def build_epub(case):
    name,kind,f=case['name'],case['kind'],case['fields']
    docs={};extra='';resources={};other='';meta=None
    if kind=='opf':
        docs={'chapter1.xhtml':page('<p>Synthetic chapter placeholder. <a href="https://example.com/nothing">Unrelated link</a></p>')}
    elif kind=='native':
        body='<div id="preface"><p><b>'+e(f['title'])+'</b><br/>Posted originally on the Archive of Our Own at <a href="'+e(f['storyUrl'])+'">Story URL</a>.</p>'+ao3_dl(f)+'</div>'
        docs={'preface.xhtml':page(body)}
        if name=='ao3-split-coauthors.epub':
            docs['preface_split_001.xhtml']=page('<div id="preface"><p>by '+authors(f)+'</p></div>')
            meta=metadata(dict(f,author=[', '.join(f['author'])]))
        else:docs['preface.xhtml']=page(body.replace('</div>','<p>by '+authors(f)+'</p></div>'))
    elif kind=='work':
        whole='whole-page' in name or 'browser' in name
        body=ao3_dl(f,nested=True,thin='thin-space' in name)
        if whole:
            body='<div id="workskin"><h2>'+e(f['title'])+'</h2><h3>by '+authors(f)+'</h3>'+body+'</div>'
            body=body.replace(' class="tags"','').replace(' class="stats"','')
        summary='<h3>Summary:</h3><blockquote>'+''.join('<p>'+e(p).replace('\n','<br/>')+'</p>' for p in f['description'].split('\n\n'))+'</blockquote><h3>Notes:</h3><blockquote><p>Synthetic notes must be excluded.</p></blockquote>'
        docs={'OEBPS/Text/0000_Information.xhtml':page(body+summary)}
        url=f.get('waybackUrl') or f.get('storyUrl')
        scheme=case.get('identifier_scheme','url')
        url_meta=('<dc:source>'+e(url)+'</dc:source>' if scheme=='source' else '<dc:identifier opf:scheme="'+scheme+'">'+e(url)+'</dc:identifier>') if url else ''
        meta=metadata(f,description=False,url=False)+url_meta
        if whole:meta=meta.replace('<dc:title>'+e(f['title'])+'</dc:title>','<dc:title>Synthetic browser page chrome [Archive of Our Own]</dc:title>')
    elif kind in ('fff_bold','fff_para','intro'):
        bold=kind=='fff_bold';path='OEBPS/title_page.xhtml' if bold else 'EPUB/introduction.xhtml' if kind=='intro' else 'OEBPS/titlepage.html'
        docs[path]=titlepage(f,bold)
        if 'cover-before' in name:docs={'titlepage.xhtml':page('<p>Synthetic empty cover page.</p>'),**docs}
        meta=metadata(f,description=True)
        if name=='fichub-ffnet-composite.epub':
            # Fichub combines labelled values in one paragraph.
            composite=' - '.join(k+': '+v for k,v in labels(f))+' - Reviews: 9 - Favs: 8 - Follows: 7'
            composite=composite.replace('Rating:','Rated:').replace('Completed','complete')
            docs[path]=page('<h1>'+e(f['title'])+'</h1><p>'+e(composite)+'</p><a href="'+e(f['storyUrl'])+'">Synthetic source</a>')
            meta=metadata(f,url=False)
    elif kind=='ffnet':
        profile=f['authorUrl'][0];story_id=f['storyUrl'].split('/s/')[1].split('/')[0]
        pub=datetime.datetime.fromisoformat(f['datePublished']).strftime('%m/%d/%Y, %I:%M:%S %p')
        upd=datetime.datetime.fromisoformat(f['dateUpdated']).strftime('%m/%d/%Y, %I:%M:%S %p')
        text='Rated: '+f['rating']+' - '+f['language']+' - '+', '.join(f['genre'])+' - '+', '.join(f['characters'])+' - Chapters: '+str(f['numChapters'])+' - Words: '+str(f['numWords'])+' - Published: '+pub+' - Updated: '+upd+' - Status: Complete - id: '+story_id
        body='<div id="pre_story_links"><a>Books</a> &gt; <a>'+e(f['fandoms'][0])+'</a></div><div id="profile_top"><b>'+e(f['title'])+'</b><a href="'+e(profile)+'">'+e(f['author'][0])+'</a><div>'+e(f['description'].replace('\n\n',' '))+'</div><span class="xgray">'+e(text)+'</span></div>'
        docs={'OEBPS/Text/0000_Information.xhtml':page(body)}
        extra='<dc:source>https://example.com/cover-image.jpg</dc:source><dc:source>'+e(f['storyUrl'])+'</dc:source>'
    elif kind=='ficlab':
        # Summary/extent disagree intentionally; timestamp/date-only display differs.
        extent=4235 if name=='ficlab-timestamp-day-boundary.epub' else f['numWords']+200
        extra='<dc:identifier>ficlab:synthetic-test</dc:identifier>'
        extra+=''.join('<dc:subject>'+e(t)+'</dc:subject>' for t in f['extratags'])
        for prop,key in [('issued','datePublished'),('modified','dateUpdated')]:extra+='<meta property="dcterms:'+prop+'">'+e(f[key].replace('+00:00','Z'))+'</meta>'
        extra+='<meta property="dcterms:extent">'+str(extent)+' words</meta>'
        summary=[('title',f['title']),('words',format(f['numWords'],',')),('chapters',f['numChapters']),('status','Complete'),('rating',f['rating']),('published','December 30th, 2012'),('updated','December 30th, 2012')]
        docs={'OEBPS/frontmatter/summary.xhtml':page('<table>'+''.join('<tr><th>'+k+'</th><td>'+e(v)+'</td></tr>' for k,v in summary)+'</table>','fl-summary'),
              'OEBPS/frontmatter/copyright.xhtml':page('<p>Synthetic test content copyrighted by <a href="'+e(f['authorUrl'][0])+'">'+e(f['author'][0])+'</a>. This entire example is invented.</p>','fl-copyright')}
        resources={'META-INF/ficlab-id':'synthetic-fixture'}
    elif kind=='pdf':
        body='<h2>Posted originally on the Archive of Our Own at</h2><p><a href="'+e(f['storyUrl'].replace('https://archiveofourown.org','http://download.archiveofourown.org'))+'">Synthetic source</a></p>'
        for key,label in [('rating','Rating'),('warnings','Archive Warning'),('ao3categories','Category'),('fandoms','Fandom'),('ships','Relationship'),('characters','Characters'),('freeformtags','Additional Tags')]:
            value=f[key];value=', '.join(value) if isinstance(value,list) else value
            # One link covers multiple comma-separated values, unlike native AO3.
            if key=='characters':
                first,rest=value.rsplit(' ',1) if ' ' in value else (value,'')
                body+='<p>'+label+': <a href="https://example.com/misaligned">'+e(first)+'</a></p><p>'+e(rest)+'</p>'
            else:
                body+='<p>'+label+': <a href="https://example.com/misaligned">'+e(value)+'</a></p>'
        if f.get('series'):
            n,idx=f['series'].rsplit(' [',1);body+='<p>Series: Part '+idx[:-1]+' of <a href="'+e(f['seriesUrl'])+'">'+e(n)+'</a></p>'
        body+='<p>Stats: '+e(' '.join(part for part in [
            'Published: '+f['datePublished'][:10], 'Updated: '+f['dateUpdated'][:10],
            'Chapters: '+f.get('chapterslashtotal','3/?'), 'Words:']))+'</p><p>'+str(f['numWords'])+'</p>'
        body+='<p> </p><p>'+e(f['title'])+'</p><p>by '+e(', '.join(f['author']))+'</p><p>Summary</p>'+ps(f['description'])+'<p>Notes</p><p>Synthetic notes excluded.</p>'
        docs={'pdf.xhtml':page(body)};meta=metadata(dict(f,author=['Unknown']),description=False,url=False)
    elif kind=='pdf_header':
        fields=[('Title',f['title']),('Rating',f.get('rating','General')),('Fandom',', '.join(f.get('fandoms',['Synthetic Fandom']))),('Pairing',', '.join(f.get('ships',['Test A/Test B']))),('Warnings',', '.join(f.get('warnings',['None']))),('Word Count','~3400')]
        body='<p>Original: <a href="'+e(f['storyUrl'])+'">Synthetic original source</a></p>'+''.join('<p>'+e(k)+': '+e(v)+'</p>' for k,v in fields)+'<p>Synthetic chapter placeholder.</p>'
        meta=metadata(f,url=False)
        docs={'pdf.xhtml':page(body,head='<meta name="generator" content="PDF reflow conversion"/>')}
    elif kind=='anthology':
        extra='<dc:contributor>epubmerge</dc:contributor>'+''.join('<dc:subject>'+e(t)+'</dc:subject>' for t in f.get('collectionTags',[]))
        for i,rec in enumerate(f['collectionRecords'],1):
            # Same minimum nested structure used by epubmerge.
            docs[f'{i}/OEBPS/title_page.xhtml']=titlepage(rec,True)
            resources[f'{i}/content.opf']=package(metadata(rec,'<dc:subject>'+e(rec.get('status','Unknown'))+'</dc:subject>'),{})
            other+=f'<item id="orig{i}" href="{i}/content.opf" media-type="origrootfile/xml"/>'
    elif kind=='series':
        body='<dl><dt>Series Begun:</dt><dd>2018-11-24</dd><dt>Series Updated:</dt><dd>2019-05-31</dd><dt>Works:</dt><dd>2</dd><dt>Words:</dt><dd>11,822</dd><dt>Complete:</dt><dd>No</dd></dl>'
        docs={'series.xhtml':page(body)};extra='<dc:identifier opf:scheme="url">'+e(f['collectionUrl'])+'</dc:identifier>'
    else:raise ValueError(kind)
    # Every book includes only a short invented body; no embedded covers/images.
    docs['synthetic-chapter.xhtml']=page('<h1>'+e(f['title'])+'</h1><p>Synthetic placeholder chapter. This file tests '+e(kind)+' metadata extraction.</p>')
    write_epub(OUT/name,f,docs,extra,resources,other,meta)


def build_txt(case):
    kind,f=case['kind'],case['fields'];title=f['title']
    if kind in ('compact','spaced'):
        lines=[title,'by '+', '.join(f['author']),''] if kind=='compact' else [title+' by '+', '.join(f['author']),'']
        ls=labels(f)
        # Archive Category is a fandom, unlike PDF preface Category.
        ls=[(k,v) for k,v in ls if k not in ('Fandom','Categories')]
        ls.append(('Publisher','fanfiction.net' if kind=='compact' else 'archiveofourown.org'))
        if f.get('storyUrl'):ls.append(('Story URL',f['storyUrl']))
        for k,v in [('Author URL',f.get('authorUrl',[''])[0] if f.get('authorUrl') else '')]:
            if v:ls.append((k,v))
        if kind=='compact':text='\n'.join(lines+[k+': '+v for k,v in ls]+['Summary: '+f['description'],'','Synthetic chapter.','Rating: Fake chapter note'])
        else:
            wrapped=[]
            for k,v in ls:
                if k=='Genre':v=v.replace(', ', ',\n')
                if k=='Ships':v=v.replace('/', '/\n')
                wrapped.append(k+': '+v)
            text='\n'.join(lines)+'\n'+ '\n\n'.join(wrapped)+'\n\nSummary:\n\n'+f['description']+'\n\n'+title+'\n\nSynthetic chapter.'
    elif kind=='txt_pdf':
        labels_=[('Rating',f['rating']),('Archive Warning',', '.join(f['warnings'])),('Category',', '.join(f['ao3categories'])),('Fandom',', '.join(f['fandoms'])),('Relationship',', '.join(f['ships'])),('Characters',', '.join(f['characters'])),('Additional Tags',', '.join(f['freeformtags'])),('Series','Part 18 of '+f['series'].rsplit(' [',1)[0]),('Stats',stats(f))]
        labels_=[(k,v.replace('Synthetic Wrapped Tag', 'Synthetic Wrapped\nTag') if k=='Additional Tags' else v) for k,v in labels_]
        text=title+'\nPosted originally on SquidgeWorld at '+f['storyUrl']+'.\n\n'+'\n'.join(k+': '+v for k,v in labels_)+'\n\n'+title+'\nby '+', '.join(f['author'])+'\n\nSummary\n\n'+f['description']+'\n\nNotes\nSynthetic notes.'
    elif kind=='partial':
        # Detached tag values have no safe positional assignment.
        text=title+'\nPosted originally on the Archive of Our Own at '+f['storyUrl']+'.\n\nRating:\nArchive Warning:\nCategory:\nFandom:\nRelationship:\nCharacters:\nAdditional Tags:\n\nGeneral Audiences\nNo Archive Warnings Apply\nM/M\nSynthetic unlabeled fandom\nTest A/Test B\nTest A, Test B\n\nStats: '+stats(f)+'\n\n'+title+'\nby Damaged test byline\n\nSummary\n\n'+f['description']+'\n\nNotes\nSynthetic notes.'
    else:text='Synthetic unsupported notice-heavy text\nTerms of use notice\nProxy notice\n\nUnlabelled metadata and ordinary placeholder prose.\n'
    (OUT/case['name']).write_text(text+'\n',encoding='utf-8')


def main():
    global OUT
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    OUT=parser.parse_args().output
    OUT.mkdir(exist_ok=True)
    for case in CASES:
        (build_txt if case['name'].endswith('.txt') else build_epub)(case)
    f=next(c['fields'] for c in CASES if c['name']=='ao3-native-complete.epub')
    parts=[]
    for key,value in f.items():
        if isinstance(value,list):
            parts.append('<ul>'+''.join('<li'+(' id="'+key+'"' if i==0 else '')+'>'+e(v)+'</li>' for i,v in enumerate(value))+'</ul>')
        else:
            parts.append('<p id="'+key+'">'+e(value)+'</p>')
    (OUT/'ao3-native-saved-metadata.html').write_text('<div>\n'+'\n'.join(parts)+'\n</div>\n')
    print('Built %d synthetic fixtures and one Saved Metadata expectation.' % len(CASES))


if __name__=='__main__':main()
