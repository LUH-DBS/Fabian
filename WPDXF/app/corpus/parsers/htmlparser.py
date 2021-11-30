import bs4
from htmlmin import minify


class HTMLParser:
    _clean_html = None

    def __init__(self, raw_html: str, charset: str = "utf-8") -> None:
        # TODO: Handle charset
        self.soup = bs4.BeautifulSoup(raw_html, "html.parser")
        # if self.soup.contains_replacement_characters or charset != "utf-8":
        #     print(charset, self.soup.original_encoding)

    @property
    def clean_html(self):
        if self._clean_html is None:
            for element in self.soup.find_all(HTMLParser.checkTags):
                element.decompose()
            # for element in self.soup.find_all(HTMLParser.checkSubtree):
            #     element.decompose()

            body = self.soup.body
            if body is None:
                # TODO: Handle webpages without a body tag
                print("Value Error by:", self.soup.prettify())
                #raise ValueError
                return ""

            # Avoid OpenTagNotFoundError which is caused by html, body or head tags inside tags that are not the main html tag.
            # If such tags exist, rename them with a general tag to preserve the structure as accurate as possible.
            # See: https://github.com/mankyd/htmlmin/blob/220b1d16442eb4b6fafed338ee3b61f698a01e63/htmlmin/parser.py#L254
            for element in body.find_all(lambda t: t.name in ("html", "body", "head")):
                element.name = "div"

            self._clean_html = minify(
                str(self.soup.body),
                remove_comments=True,
                remove_empty_space=True,
                reduce_empty_attributes=False,
            )

        return self._clean_html

    @staticmethod
    def checkTags(tag: bs4.element.Tag) -> bool:
        return tag.name in ["script", "style"]

    @staticmethod
    def checkSubtree(tag: bs4.element.Tag) -> bool:
        """Subtrees without text can be neglected. 
        The subtree's root node is retained to keep the general structure. 

        Remove 'node' if the tree fulfills the following structure:        
        pparent [contains text] --> parent [no text] --> node [no text]

        Args:
            tag (bs4.element.Tag): The 'node'

        Returns:
            bool: True, if the node fulfills the condition.
        """
        if len(tag.get_text()) > 0:
            return False
        parent = tag.parent
        if parent is None or len(parent.get_text()) > 0:
            return False
        pparent = parent.parent
        if pparent is None or len(pparent.get_text()) == 0:
            return False
        return True
