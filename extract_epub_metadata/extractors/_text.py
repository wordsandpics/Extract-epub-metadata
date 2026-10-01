"""Plain-text presentation of HTML metadata, without losing paragraph boundaries."""
import re
from html.parser import HTMLParser


class _MetadataText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif not self.hidden:
            if tag == 'br':
                self.parts.append('\n')
            elif tag in ('p', 'div', 'blockquote', 'li'):
                self.parts.append('\n\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in ('p', 'div', 'blockquote', 'li'):
            self.parts.append('\n\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_to_text(value):
    if not value:
        return value
    parser = _MetadataText()
    parser.feed(value)
    parser.close()
    text = ''.join(parser.parts)
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()
