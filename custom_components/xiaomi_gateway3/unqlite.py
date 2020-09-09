class Unqlite:
    page_size = 0
    pos = 0

    def __init__(self, raw: bytes):
        self.raw = raw
        self.read_db_header()

    @property
    def size(self):
        return len(self.raw)

    def read(self, length: int):
        self.pos += length
        return self.raw[self.pos - length:self.pos]

    def read_int(self, length: int):
        return int.from_bytes(self.read(length), 'big')

    def read_db_header(self):
        assert self.read(7) == b'unqlite', "Wrong file signature"
        assert self.read(4) == b'\xDB\x7C\x27\x12', "Wrong DB magic"
        creation_time = self.read_int(4)
        sector_size = self.read_int(4)
        self.page_size = self.read_int(4)
        assert self.read(6) == b'\x00\x04hash', "Unsupported hash"

    # def read_header2(self):
    #     self.pos = self.page_size
    #     magic_numb = self.read(4)
    #     hash_func = self.read(4)
    #     free_pages = self.read_int(8)
    #     split_bucket = self.read_int(8)
    #     max_split_bucket = self.read_int(8)
    #     next_page = self.read_int(8)
    #     num_rect = self.read_int(4)
    #     for _ in range(num_rect):
    #         logic_page = self.read_int(8)
    #         real_page = self.read_int(8)

    def read_cell(self):
        key_hash = self.read(4)
        key_len = self.read_int(4)
        data_len = self.read_int(8)
        next_offset = self.read_int(2)
        overflow_page = self.read_int(8)
        if overflow_page:
            self.pos = overflow_page * 0x1000 + 8
            data_page = self.read_int(8)
            data_offset = self.read_int(2)
            name = self.read(key_len)
            self.pos = data_page * 0x1000 + data_offset
            value = self.read(data_len)
        else:
            name = self.read(key_len)
            value = self.read(data_len)
        return name, value, next_offset

    def read_all(self) -> dict:
        result = {}

        page_offset = 2 * self.page_size
        while page_offset < self.size:
            self.pos = page_offset
            next_offset = self.read_int(2)
            while next_offset:
                self.pos = page_offset + next_offset
                k, v, next_offset = self.read_cell()
                result[k.decode()] = v.decode()
            page_offset += self.page_size

        return result
