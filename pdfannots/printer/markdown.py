import logging
import textwrap
import typing as typ

from . import Printer
from ..types import AnnotationType, Pos, Annotation, Document

logger = logging.getLogger('pdfannots')

MAX_CONTEXT_WORDS = 256
"""Maximum number of words returned by trim_context."""

FALLBACK_CONTEXT_WORDS = 4
"""Number of words returned by trim_context in fallback mode."""

CONTEXT_BOUNDARIES = [
    # (separator, keep_on_left, keep_on_right)
    ('. ', False, True),  # sentence boundary
    ('! ', False, True),
    ('? ', False, True),
    # (': ', False, False),
    # ('; ', False, False),
    # ('" ', False, True),   # end of quote
    # (' "', True, False),   # start of quote
    # (') ', False, True),   # end of parenthesis
    # (' (', True, False),   # start of parenthesis
    # ('—', False, False),   # em dash
]
"""Rough approximation of natural boundaries in writing, used when searching for context."""


def trim_context(context: str, keep_right: bool) -> str:
    """
    Trim context for presentation.

    Given a potentially-long string of context preceding or following an annotation, identify
    a natural boundary at which to trim it, and return the trimmed string.

    Arguments:
        context     String of captured context
        keep_right  Whether to retain text on the right (True) or left (False) end of the string
    """
    best = None

    for (sep, keep_sep_left, keep_sep_right) in CONTEXT_BOUNDARIES:
        # search for the separator
        i = context.rfind(sep) if keep_right else context.find(sep)
        if i < 0:
            continue

        # include the separator if desired
        if (keep_right and not keep_sep_left) or (not keep_right and keep_sep_right):
            i += len(sep)

        # extract the candidate string
        candidate = context[i:] if keep_right else context[:i]

        if best is None or len(candidate) < len(best):
            best = candidate
            if len(candidate.split()) <= 1:
                break

    if best is not None and len(best.split()) <= MAX_CONTEXT_WORDS:
        return best

    # Give up and take a few words, whatever they are.
    if keep_right:
        fallback = '...' + ' '.join(context.split()[-FALLBACK_CONTEXT_WORDS:])
        if context[-1].isspace():
            fallback += context[-1]
    else:
        fallback = ' '.join(context.split()[:FALLBACK_CONTEXT_WORDS]) + '...'
        if context[0].isspace():
            fallback = context[0] + fallback

    return fallback


class MarkdownPrinter(Printer):
    BULLET_INDENT1 = " * "
    BULLET_INDENT2 = "   "
    QUOTE_INDENT = BULLET_INDENT2 + "> "
    SO_WORDS = []
    UL_WORDS = []

    def __init__(
        self,
        *,
        condense: bool = True,                  # Permit use of the condensed format
        print_filename: bool = False,           # Whether to print file names
        remove_hyphens: bool = True,            # Whether to remove hyphens across a line break
        wrap_column: typ.Optional[int] = None,  # Column at which output is word-wrapped
        **kwargs: typ.Any                       # Other args, ignored
    ) -> None:
        self.print_filename = print_filename
        self.remove_hyphens = remove_hyphens
        self.wrap_column = wrap_column
        self.condense = condense

        if self.wrap_column:
            # For bullets, we need two text wrappers: one for the leading
            # bullet on the first paragraph, one without.
            self.bullet_tw1 = textwrap.TextWrapper(
                width=self.wrap_column,
                initial_indent=self.BULLET_INDENT1,
                subsequent_indent=self.BULLET_INDENT2)

            self.bullet_tw2 = textwrap.TextWrapper(
                width=self.wrap_column,
                initial_indent=self.BULLET_INDENT2,
                subsequent_indent=self.BULLET_INDENT2)

            # For blockquotes, each line is prefixed with "> "
            self.quote_tw = textwrap.TextWrapper(
                width=self.wrap_column,
                initial_indent=self.QUOTE_INDENT,
                subsequent_indent=self.QUOTE_INDENT)

    def print_file(
        self,
        filename: str,
        document: Document
    ) -> typ.Iterator[str]:
        body_iter = self.emit_body(document)

        if self.print_filename:
            # Print the file name, only if there is some output.
            try:
                first = next(body_iter)
            except StopIteration:
                pass
            else:
                yield "# File: '%s'\n\n" % filename
                yield first

        yield from body_iter

    @staticmethod
    def format_pos(
        pos: Pos,
        document: Document
    ) -> str:

        result = str(pos.page).title()

        o = document.nearest_outline(pos)
        if o:
            result += " (%s)" % o.title

        return result

    def format_bullet(
        self,
        paras: typ.List[str],
        quote: typ.Optional[typ.Tuple[int, int]] = None
    ) -> str:
        """
        Format a Markdown bullet, wrapped as desired.
        """

        if quote is not None:
            (quotepos, quotelen) = quote
            assert quotepos > 0  # first paragraph to format as a block-quote
            assert quotelen > 0  # length of the blockquote in paragraphs
            assert quotepos + quotelen <= len(paras)

        # emit the first paragraph with the bullet
        if self.wrap_column:
            ret = self.bullet_tw1.fill(paras[0])
        else:
            ret = self.BULLET_INDENT1 + paras[0]

        # emit subsequent paragraphs
        npara = 1
        for para in paras[1:]:
            # are we in a blockquote?
            inquote = quote and npara >= quotepos and npara < quotepos + quotelen

            # emit a paragraph break
            # if we're going straight to a quote, we don't need an extra newline
            ret = ret + ('\n\n' if quote and npara <= quotepos else '\n'+ self.QUOTE_INDENT+ '\n')

            if self.wrap_column:
                tw = self.quote_tw if inquote else self.bullet_tw2
                ret = ret + tw.fill(para)
            else:
                indent = self.QUOTE_INDENT if inquote else self.BULLET_INDENT2
                ret = ret + indent + para

            npara += 1

        return ret

    def merge_context(self, annot: Annotation, text: str) -> str:
        """Merge the context for an annotation into the text."""
        (pre, post) = annot.get_context(self.remove_hyphens)

        if pre:
            pre = trim_context(pre, keep_right=True)

        if post:
            post = trim_context(post, keep_right=False)

        return pre + text + post
    
    def sub_text(self, text: str, so_words: list, ul_words: list) -> str:
        """substitute each word of words with <u>word</u> or ~~word~~ in text"""
        words = so_words + ul_words
        words_deco = ["~~" + word + "~~" for word in so_words]\
            + ["<u>" + word + "</u>" for word in ul_words]
        for word, word_deco in zip(words, words_deco):
            text = text.replace(word, word_deco)
        return text

    def format_annot(
        self,
        annot: Annotation,
        document: Document,
        extra: typ.Optional[str] = None,
        next_annot: Annotation = None
    ) -> str:

        # capture item text and contents (i.e. the comment), and split the latter into paragraphs
        text = annot.gettext(self.remove_hyphens) or ''
        next_text = next_annot.gettext(self.remove_hyphens) or ''\
            if next_annot else None
        comment = ([l for l in annot.contents.splitlines() if l]
                   if annot.contents else [])

        if annot.has_context():
            assert annot.subtype in [AnnotationType.StrikeOut, AnnotationType.Underline]
            if next_annot:
                assert next_annot.subtype in [AnnotationType.StrikeOut, AnnotationType.Underline]
            if annot.subtype is AnnotationType.StrikeOut:
                text_deco = "~~" + text + "~~"
            if annot.subtype is AnnotationType.Underline:
                text_deco = "<u>" + text + "</u>"

            text_merged = self.merge_context(annot, text)
            next_text_merged = self.merge_context(next_annot, next_text)\
                if next_text else None
            
            text_merged_deco = self.merge_context(annot, text_deco)
            
            # if the next text with context merged is same with the current text
            # with context merged, then do not output the current text
            if (next_text_merged and text_merged == next_text_merged):
                if annot.subtype is AnnotationType.StrikeOut:
                    self.SO_WORDS.append(text)
                if annot.subtype is AnnotationType.Underline:
                    self.UL_WORDS.append(text)
                text = " "
            # output the current text with all of the annotation words decorated
            # properly
            else:
                text = self.sub_text(text_merged_deco, self.SO_WORDS, self.UL_WORDS) if (self.SO_WORDS or self.UL_WORDS) else text_merged_deco
                self.SO_WORDS.clear()
                self.UL_WORDS.clear()

        # we are either printing: item text and item contents, or one of the two
        # if we see an annotation with neither, something has gone wrong
        if not (text or comment):
            logger.warning('%s annotation at %s has neither text nor a comment; skipped',
                           annot.subtype.name, annot.pos)
            return ''

        # compute the formatted position (and extra bit if needed) as a label
        assert annot.pos is not None
        label = self.format_pos(annot.pos, document) + \
            (" " + extra if extra else "")

        # For Highlights, if we have one line text with one line or no comment,
        # then we'll just bold the text and merge the two into a single paragraph.
        if (self.condense
            and text
            and not annot.has_context()  # just for Highlights
            and len(text.splitlines()) == 1  # one line
            and (not comment or len(comment) == 1)):
            msg = label + ' **' + text + '**'
            if comment:
                msg = msg + ' -- ' + comment[0]
            return self.format_bullet([msg]) + "\n\n"

        # If there is no text and a single-paragraph comment, it also goes on
        # one line.
        elif comment and not text and len(comment) == 1:
            msg = label + " " + comment[0]
            return self.format_bullet([msg]) + "\n\n"
        
        # For StrikeOut and Underline, if we have text with a short or no comment,
        # then we'll just bold the text and merge the two into a single paragraph,
        # and turns the text (if any) into a blockquote;
        # if we have text with multi lines comment, then we put the comment into
        # subsequent paragraphs, and turns the text (if any) into a blockquote.
        elif (annot.has_context()):
            if (not comment or len(comment) == 1):
                label = label + ' -- ' + comment[0] if comment else label
                msgparas = [label] + [text] if text != " " else [label]
                quote = (1, 1) if text and text!=" " else None
            else:
                msgparas = [label] + comment + [text]
                quotepos = len(comment)+1 if comment else 1
                quote = (quotepos, 1) if text else None
            return self.format_bullet(msgparas, quote) + "\n\n"

        # Otherwise, bold the text (if any) and put it into a subsequent
        # paragraph, turns the comment (if any) into a blockquote.
        else:
            text = "**"+text+"**"
            msgparas = [label] + [text] + comment
            quotelen = len(comment) if comment else 0
            quote = (2, quotelen) if text else None
            return self.format_bullet(msgparas, quote) + "\n\n"

    def emit_body(
        self,
        document: Document
    ) -> typ.Iterator[str]:
        for a in document.iter_annots():
            yield self.format_annot(a, document, a.subtype.name)


class GroupedMarkdownPrinter(MarkdownPrinter):
    ANNOT_NITS = frozenset({
        AnnotationType.Squiggly, AnnotationType.StrikeOut, AnnotationType.Underline})
    ALL_SECTIONS = ["highlights", "comments", "nits"]

    def __init__(
        self,
        *,
        sections: typ.Sequence[str] = ALL_SECTIONS,  # controls the order of sections output
        **kwargs: typ.Any                            # other args -- see superclass
    ) -> None:
        super().__init__(**kwargs)
        self.sections = sections
        self._fmt_header_called: bool

    def emit_body(
        self,
        document: Document
    ) -> typ.Iterator[str]:

        self._fmt_header_called = False

        def fmt_header(name: str) -> str:
            # emit blank separator line if needed
            prefix = '\n' if self._fmt_header_called else ''
            self._fmt_header_called = True
            return prefix + "## " + name + "\n\n"

        # Partition annotations into nits, comments, and highlights.
        nits = []
        comments = []
        highlights = []
        for a in document.iter_annots():
            if a.subtype in self.ANNOT_NITS:
                nits.append(a)
            elif a.contents:
                comments.append(a)
            elif a.subtype == AnnotationType.Highlight:
                highlights.append(a)

        for secname in self.sections:
            if highlights and secname == 'highlights':
                yield fmt_header("Highlights")
                for a in highlights:
                    yield self.format_annot(a, document)

            if comments and secname == 'comments':
                yield fmt_header("Detailed comments")
                for a in comments:
                    yield self.format_annot(a, document)

            if nits and secname == 'nits':
                yield fmt_header("Corpus")
                for i, a in enumerate(nits):
                    next_a = nits[i+1] if i<=len(nits)-2 else None
                    if a.subtype is AnnotationType.StrikeOut:
                        extra = "~~"+a.gettext(self.remove_hyphens)+"~~"
                    elif a.subtype is AnnotationType.Underline:
                        extra = "**"+a.gettext(self.remove_hyphens)+"**"
                    else:
                        None
                    yield self.format_annot(a, document, extra, next_a)
