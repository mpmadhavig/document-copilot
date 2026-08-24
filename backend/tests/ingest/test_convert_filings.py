from docling_core.types.doc.document import TableCell, TableData, TableItem

from ingest.convert_filings import add_markdown_headings, normalize_table


def cell(row: int, start: int, end: int, text: str) -> TableCell:
    return TableCell(
        start_row_offset_idx=row,
        end_row_offset_idx=row + 1,
        start_col_offset_idx=start,
        end_col_offset_idx=end,
        text=text,
    )


def grid_text(table: TableItem) -> list[list[str]]:
    return [[cell.text for cell in row] for row in table.data.grid]


def test_normalize_table_collapses_spans_and_financial_affixes() -> None:
    table = TableItem(
        self_ref="#/tables/0",
        data=TableData(
            num_rows=5,
            num_cols=18,
            table_cells=[
                cell(1, 3, 18, "Years ended"),
                cell(2, 3, 6, "2023"),
                cell(2, 9, 12, "2022"),
                cell(2, 15, 18, "2021"),
                cell(3, 0, 3, "Products"),
                cell(3, 3, 4, "$"),
                cell(3, 4, 5, "100"),
                cell(3, 9, 10, "$"),
                cell(3, 10, 11, "90"),
                cell(3, 15, 16, "$"),
                cell(3, 16, 17, "80"),
                cell(4, 0, 3, "Services"),
                cell(4, 3, 5, "50"),
                cell(4, 9, 11, "40"),
                cell(4, 15, 17, "30"),
            ],
        ),
    )

    normalize_table(table)

    assert table.data.num_cols == 4
    assert grid_text(table) == [
        ["", "Years ended", "", ""],
        ["", "2023", "2022", "2021"],
        ["Products", "$ 100", "$ 90", "$ 80"],
        ["Services", "50", "40", "30"],
    ]


def test_normalize_table_preserves_missing_value_alignment() -> None:
    table = TableItem(
        self_ref="#/tables/0",
        data=TableData(
            num_rows=2,
            num_cols=9,
            table_cells=[
                cell(0, 0, 3, "Customer A"),
                cell(0, 3, 6, "12%"),
                cell(0, 6, 9, "13%"),
                cell(1, 0, 3, "Customer B"),
                cell(1, 6, 9, "*"),
            ],
        ),
    )

    normalize_table(table)

    assert grid_text(table) == [
        ["Customer A", "12%", "13%"],
        ["Customer B", "", "*"],
    ]


def test_normalize_table_does_not_merge_dash_placeholder() -> None:
    table = TableItem(
        self_ref="#/tables/0",
        data=TableData(
            num_rows=2,
            num_cols=9,
            table_cells=[
                cell(0, 0, 3, "Security"),
                cell(0, 3, 6, "Symbol"),
                cell(0, 6, 9, "Exchange"),
                cell(1, 0, 3, "Notes due 2027"),
                cell(1, 3, 6, "-"),
                cell(1, 6, 9, "Nasdaq"),
            ],
        ),
    )

    normalize_table(table)

    assert grid_text(table)[1] == ["Notes due 2027", "-", "Nasdaq"]


def test_normalize_table_removes_empty_layout_table() -> None:
    table = TableItem(
        self_ref="#/tables/0",
        data=TableData(
            num_rows=1,
            num_cols=3,
            table_cells=[cell(0, 0, 1, ""), cell(0, 1, 2, "")],
        ),
    )

    normalize_table(table)

    assert table.data.num_rows == 0
    assert table.data.num_cols == 0


def test_add_markdown_headings_promotes_only_section_labels() -> None:
    markdown = """PART I
ITEM 1A. RISK FACTORS
CONSOLIDATED STATEMENTS OF OPERATIONS
This remains ordinary prose.
| TABLE VALUE |"""

    assert add_markdown_headings(markdown) == """## PART I
## ITEM 1A. RISK FACTORS
## CONSOLIDATED STATEMENTS OF OPERATIONS
This remains ordinary prose.
| TABLE VALUE |
"""
