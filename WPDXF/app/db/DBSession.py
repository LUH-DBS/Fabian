from warcio.recordloader import ArcWarcRecord

class DBSession:
    CHUNK_SIZE = 1000
    
    def beforeInsert(self, *args, **kwargs):
        pass

    def insertHTML(self, warc: ArcWarcRecord):
        raise NotImplementedError

    def insertTerms(self, wet: ArcWarcRecord):
        raise NotImplementedError

    def submit(self):
        pass

    def afterInsert(self):
        pass
