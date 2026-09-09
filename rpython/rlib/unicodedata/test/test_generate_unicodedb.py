import zipfile

from rpython.rlib.unicodedata import generate_unicodedb


def test_data_url():
    assert generate_unicodedb._data_url(
        'UnicodeData-14.0.0.txt', '14.0.0') == (
            'https://www.unicode.org/Public/14.0.0/ucd/UnicodeData.txt')
    assert generate_unicodedb._data_url(
        'UnicodeData-3.2.0.txt', '3.2.0') == (
            'https://www.unicode.org/Public/3.2-Update/'
            'UnicodeData-3.2.0.txt')
    assert generate_unicodedb._data_url(
        'UnihanNumeric-14.0.0.txt', '14.0.0') == (
            'https://www.unicode.org/Public/14.0.0/ucd/Unihan.zip')
    assert generate_unicodedb._data_url(
        'UnihanNumeric-3.2.0.txt', '3.2.0') == (
            'https://www.unicode.org/Public/3.2-Update/'
            'Unihan-3.2.0.zip')


def test_open_data_downloads_missing_file(tmpdir, monkeypatch):
    def download(url, filename):
        assert url.endswith('/UnicodeData.txt')
        with open(filename, 'w') as output:
            output.write('0041;LATIN CAPITAL LETTER A\n')

    monkeypatch.setattr(generate_unicodedb, '_urlretrieve', download)
    data = generate_unicodedb.open_data(
        'UnicodeData-14.0.0.txt', '14.0.0', str(tmpdir))
    try:
        assert data.read() == '0041;LATIN CAPITAL LETTER A\n'
    finally:
        data.close()


def test_open_data_extracts_unihan_numeric_values(tmpdir, monkeypatch):
    def download(url, filename):
        assert url.endswith('/Unihan.zip')
        archive = zipfile.ZipFile(filename, 'w')
        try:
            archive.writestr('Unihan_NumericValues.txt',
                             'U+3405\tkPrimaryNumeric\t5\n')
        finally:
            archive.close()

    monkeypatch.setattr(generate_unicodedb, '_urlretrieve', download)
    data = generate_unicodedb.open_data(
        'UnihanNumeric-14.0.0.txt', '14.0.0', str(tmpdir))
    try:
        assert data.read() == 'U+3405\tkPrimaryNumeric\t5\n'
    finally:
        data.close()


def test_open_data_filters_unihan_3_2(tmpdir, monkeypatch):
    def download(url, filename):
        assert url.endswith('/Unihan-3.2.0.zip')
        archive = zipfile.ZipFile(filename, 'w')
        try:
            archive.writestr(
                'Unihan-3.2.0.txt',
                'U+3405\tkPrimaryNumeric\t5\n'
                'U+3405\tkDefinition\tfive\n')
        finally:
            archive.close()

    monkeypatch.setattr(generate_unicodedb, '_urlretrieve', download)
    data = generate_unicodedb.open_data(
        'UnihanNumeric-3.2.0.txt', '3.2.0', str(tmpdir))
    try:
        assert data.read() == 'U+3405\tkPrimaryNumeric\t5\n'
    finally:
        data.close()


def test_open_data_creates_empty_file_for_missing_3_2_data(tmpdir,
                                                            monkeypatch):
    def download(url, filename):
        raise AssertionError("should not download a file that never existed")

    monkeypatch.setattr(generate_unicodedb, '_urlretrieve', download)
    data = generate_unicodedb.open_data(
        'NameAliases-3.2.0.txt', '3.2.0', str(tmpdir))
    try:
        assert data.read() == ''
    finally:
        data.close()
