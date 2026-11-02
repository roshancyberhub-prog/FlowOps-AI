import pytest

from app.leads.csv_import import ImportValidation, inspect_csv, parse_csv


def test_csv_normalizes_and_reports_bad_and_duplicate_records():
    data = (
        b"name,email,company\nFirst Buyer, FIRST@example.com ,Acme\n"
        b"Invalid,bad-email,Acme\nDuplicate,first@example.com,Acme\n"
    )
    result = parse_csv(data, {"name": "name", "email": "email", "company": "company"})
    assert len(result) == 3
    assert result[0].data["email"] == "first@example.com"
    assert result[1].errors
    assert result[2].duplicate_in_file
    assert [row.number for row in result] == [2, 3, 4]


def test_csv_handles_bom_quoted_commas_and_newlines():
    data = (
        '\ufeffFull Name,Email,Company\r\n"Buyer, One",buyer@example.com,"Company\nTwo"\r\n'
    ).encode()
    assert inspect_csv(data)["headers"] == ["Full Name", "Email", "Company"]
    rows = parse_csv(data, {"name": "Full Name", "email": "Email", "company": "Company"})
    assert rows[0].data["name"] == "Buyer, One"
    assert rows[0].data["company"] == "Company\nTwo"


@pytest.mark.parametrize(
    "data,mapping",
    [
        (b"name,name\nA,B", {"name": "name", "email": "name"}),
        (b"name,email\nA,a@example.com", {"name": "name"}),
        (b"name,email\nA,a@example.com", {"name": "name", "email": "email", "status": "name"}),
        (b"name,email\nA,a@example.com", {"name": "missing", "email": "email"}),
        (b"\xff\xfe", {}),
        (b"name,email\x00\nA,a@example.com", {}),
    ],
)
def test_invalid_files_or_mappings_are_rejected(data, mapping):
    with pytest.raises(ImportValidation):
        parse_csv(data, mapping)


def test_csv_enforces_file_row_and_cell_limits_before_processing():
    for data in [
        b"x" * (512 * 1024 + 1),
        b"name,email\n" + b"A,a@example.com\n" * 2001,
        b"name,email\n" + b"A" * 2049 + b",a@example.com\n",
    ]:
        with pytest.raises(ImportValidation):
            parse_csv(data, {"name": "name", "email": "email"})
