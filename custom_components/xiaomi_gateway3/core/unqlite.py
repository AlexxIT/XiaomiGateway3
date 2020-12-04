"""Two classes for read Unqlite and SQLite DB files frow raw bytes. Default
python sqlite3 library can't read DB from memory.
"""


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


class SQLite:
    page_size = 0
    pos = 0

    def __init__(self, raw: bytes):
        self.raw = raw
        self.read_db_header()
        self.tables = self.read_page(0)

    @property
    def size(self):
        return len(self.raw)

    def read(self, length: int):
        self.pos += length
        return self.raw[self.pos - length:self.pos]

    def read_int(self, length: int):
        return int.from_bytes(self.read(length), 'big')

    def read_varint(self):
        result = 0
        while True:
            i = self.read_int(1)
            result += i & 0x7f
            if i < 0x80:
                break
            result <<= 7

        return result

    def read_db_header(self):
        assert self.read(16) == b'SQLite format 3\0', "Wrong file signature"
        self.page_size = self.read_int(2)

    def read_page(self, page_num: int):
        self.pos = 100 if page_num == 0 else self.page_size * page_num

        # B-tree Page Header Format
        page_type = self.read(1)

        if page_type == b'\x0D':
            return self._read_leaf_table(page_num)
        elif page_type == b'\x05':
            return self._read_interior_table(page_num)
        else:
            raise NotImplemented

    def _read_leaf_table(self, page_num: int):
        first_block = self.read_int(2)
        cells_num = self.read_int(2)
        cells_pos = self.read_int(2)
        fragmented_free_bytes = self.read_int(1)

        cells_pos = [self.read_int(2) for _ in range(cells_num)]
        rows = []

        for cell_pos in cells_pos:
            self.pos = self.page_size * page_num + cell_pos

            payload_len = self.read_varint()
            rowid = self.read_varint()

            columns_type = []

            payload_pos = self.pos
            header_size = self.read_varint()
            while self.pos < payload_pos + header_size:
                column_type = self.read_varint()
                columns_type.append(column_type)

            cells = []

            for column_type in columns_type:
                if column_type == 0:
                    data = rowid
                elif 1 <= column_type <= 4:
                    data = self.read_int(column_type)
                elif column_type == 5:
                    data = self.read_int(6)
                elif column_type == 6:
                    data = self.read_int(8)
                elif column_type == 7:
                    # TODO: float
                    data = self.read(8)
                elif column_type == 8:
                    data = 0
                elif column_type == 9:
                    data = 1
                elif column_type >= 12 and column_type % 2 == 0:
                    length = int((column_type - 12) / 2)
                    data = self.read(length)
                else:
                    length = int((column_type - 13) / 2)
                    data = self.read(length).decode()

                cells.append(data)

            rows.append(cells)

        return rows

    def _read_interior_table(self, page_num: int):
        first_block = self.read_int(2)
        cells_num = self.read_int(2)
        cells_pos = self.read_int(2)
        fragmented_free_bytes = self.read_int(1)
        last_page_num = self.read_int(4)

        cells_pos = [self.read_int(2) for _ in range(cells_num)]
        rows = []

        for cell_pos in cells_pos:
            self.pos = self.page_size * page_num + cell_pos
            child_page_num = self.read_int(4)
            rowid = self.read_varint()
            rows += self.read_page(child_page_num - 1)

        return rows + self.read_page(last_page_num - 1)

    def read_table(self, name: str):
        page = next(t[3] - 1 for t in self.tables if t[1] == name)
        return self.read_page(page)
