"""Convert SEC filing HTML to retrieval-friendly Markdown."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import (
    MarkdownDocSerializer,
    MarkdownTableSerializer,
)
from docling_core.types.doc.document import (
    DoclingDocument,
    RichTableCell,
    TableCell,
    TableData,
    TableItem,
)

Cell = TableCell | RichTableCell


@dataclass
class CellRun:
    start: int
    end: int
    text: str
    source_cells: list[Cell]


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _join_affix(left: str, right: str) -> str:
    text = f"{left} {right}"
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+([)%])", r"\1", text)
    text = re.sub(r"([-+])\s+(?=\d)", r"\1", text)
    return text


def _merge_financial_affixes(cells: list[CellRun]) -> list[CellRun]:
    merged: list[CellRun] = []
    prefixes = {"$", "£", "€", "¥", "("}
    suffixes = {")", "%"}

    for cell in cells:
        if (
            merged
            and merged[-1].end == cell.start
            and (merged[-1].text in prefixes or cell.text in suffixes)
        ):
            previous = merged[-1]
            previous.end = cell.end
            previous.text = _join_affix(previous.text, cell.text)
            previous.source_cells.extend(cell.source_cells)
        else:
            merged.append(cell)

    return merged


def _table_rows(data: TableData) -> list[list[CellRun]]:
    rows: list[list[CellRun]] = []
    for row_index in range(data.num_rows):
        cells = sorted(
            (
                cell
                for cell in data.table_cells
                if cell.start_row_offset_idx == row_index and _clean_text(cell.text)
            ),
            key=lambda cell: cell.start_col_offset_idx,
        )
        rows.append(
            _merge_financial_affixes(
                [
                    CellRun(
                        start=cell.start_col_offset_idx,
                        end=cell.end_col_offset_idx,
                        text=_clean_text(cell.text),
                        source_cells=[cell],
                    )
                    for cell in cells
                ]
            )
        )
    return [row for row in rows if row]


def _numeric_cell_count(row: list[CellRun]) -> int:
    return sum(bool(re.search(r"\d", cell.text)) for cell in row)


def _canonical_columns(rows: list[list[CellRun]]) -> list[tuple[int, int]]:
    representative = max(
        rows,
        key=lambda row: (len(row), _numeric_cell_count(row)),
    )
    return [(cell.start, cell.end) for cell in representative]


def _column_for(cell: CellRun, columns: list[tuple[int, int]]) -> int:
    overlaps = [
        max(0, min(cell.end, end) - max(cell.start, start))
        for start, end in columns
    ]
    largest_overlap = max(overlaps)
    if largest_overlap:
        return overlaps.index(largest_overlap)

    midpoint = (cell.start + cell.end) / 2
    return min(
        range(len(columns)),
        key=lambda index: abs(midpoint - sum(columns[index]) / 2),
    )


def _plain_cell(text: str, row: int, column: int) -> TableCell:
    return TableCell(
        start_row_offset_idx=row,
        end_row_offset_idx=row + 1,
        start_col_offset_idx=column,
        end_col_offset_idx=column + 1,
        text=text,
        column_header=row == 0,
    )


def _output_cell(runs: list[CellRun], row: int, column: int) -> Cell:
    if not runs:
        return _plain_cell("", row, column)

    if len(runs) == 1 and len(runs[0].source_cells) == 1:
        source = runs[0].source_cells[0]
        return source.model_copy(
            update={
                "row_span": 1,
                "col_span": 1,
                "start_row_offset_idx": row,
                "end_row_offset_idx": row + 1,
                "start_col_offset_idx": column,
                "end_col_offset_idx": column + 1,
                "text": runs[0].text,
                "column_header": row == 0,
            }
        )

    return _plain_cell(" ".join(run.text for run in runs), row, column)


def _normalized_rows(data: TableData) -> list[list[list[CellRun]]]:
    rows = _table_rows(data)
    if not rows:
        return []
    columns = _canonical_columns(rows)
    normalized: list[list[list[CellRun]]] = []
    for row in rows:
        mapped: list[list[CellRun]] = [[] for _ in columns]
        for cell in row:
            mapped[_column_for(cell, columns)].append(cell)
        normalized.append(mapped)
    return normalized


def normalize_table(table: TableItem) -> None:
    """Collapse presentation-grid spans into compact semantic columns."""
    rows = _normalized_rows(table.data)
    if not rows:
        table.data = TableData()
        return

    output_cells: list[Cell] = []
    for row_index, row in enumerate(rows):
        output_cells.extend(
            _output_cell(runs, row_index, column_index)
            for column_index, runs in enumerate(row)
        )

    table.data = TableData(
        table_cells=output_cells,
        num_rows=len(rows),
        num_cols=len(rows[0]),
        orientation=table.data.orientation,
    )


def normalize_document_tables(document: DoclingDocument) -> None:
    for table in document.tables:
        normalize_table(table)


class SemanticMarkdownTableSerializer(MarkdownTableSerializer):
    """Serialize logical cells instead of expanding the HTML layout grid."""

    def _render_run(
        self,
        run: CellRun,
        doc_serializer: MarkdownDocSerializer,
        document: DoclingDocument,
        kwargs: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        for cell in run.source_cells:
            if isinstance(cell, RichTableCell):
                text = doc_serializer.serialize(
                    item=cell.ref.resolve(doc=document),
                    **kwargs,
                    _nested_in_table=True,
                ).text
            else:
                text = cell.text
            parts.append(_clean_text(text))

        rendered = parts[0]
        for part in parts[1:]:
            rendered = _join_affix(rendered, part)
        return rendered

    def serialize(
        self,
        *,
        item: TableItem,
        doc_serializer: MarkdownDocSerializer,
        doc: DoclingDocument,
        **kwargs: Any,
    ) -> Any:
        if kwargs.get("_nested_in_table"):
            return super().serialize(
                item=item,
                doc_serializer=doc_serializer,
                doc=doc,
                **kwargs,
            )

        caption = doc_serializer.serialize_captions(item=item, **kwargs)
        rows = _normalized_rows(item.data)
        if not rows:
            return caption

        rendered_rows: list[list[str]] = []
        for row in rows:
            rendered_row: list[str] = []
            for runs in row:
                text = " ".join(
                    self._render_run(run, doc_serializer, doc, kwargs)
                    for run in runs
                )
                rendered_row.append(
                    text.replace("\n", " ").replace("|", "&#124;")
                )
            rendered_rows.append(rendered_row)

        table_lines = [
            "| " + " | ".join(row) + " |" for row in rendered_rows
        ]
        table_lines.insert(
            1,
            "| " + " | ".join("---" for _ in rows[0]) + " |",
        )
        table_text = "\n".join(table_lines)
        text = "\n\n".join(part for part in (caption.text, table_text) if part)
        return create_ser_result(text=text, span_source=item)


_PART_HEADING = re.compile(r"^PART\s+[IVX]+$")
_ITEM_HEADING = re.compile(r"^ITEM\s+\d+[A-Z]?(?:\.|\s|$)")


def add_markdown_headings(markdown: str) -> str:
    """Promote short SEC section labels without rewriting prose."""
    output: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        letters = [character for character in stripped if character.isalpha()]
        is_uppercase_label = (
            3 <= len(stripped) <= 100
            and len(letters) >= 4
            and all(character.isupper() for character in letters)
            and not stripped.endswith(".")
        )
        if (
            stripped
            and not stripped.startswith(("#", "|", "<!--"))
            and (
                _PART_HEADING.match(stripped)
                or _ITEM_HEADING.match(stripped)
                or is_uppercase_label
            )
        ):
            output.append(f"## {stripped}")
        else:
            output.append(line)
    return "\n".join(output).rstrip() + "\n"


def convert_file(
    source: Path,
    destination: Path,
    converter: DocumentConverter,
) -> None:
    result = converter.convert(source)
    serializer = MarkdownDocSerializer(
        doc=result.document,
        table_serializer=SemanticMarkdownTableSerializer(),
    )
    markdown = serializer.serialize(
        image_placeholder="<!-- source image omitted -->",
        compact_tables=True,
    ).text
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(add_markdown_headings(markdown), encoding="utf-8")


def convert_corpus(source_dir: Path, destination_dir: Path) -> int:
    sources = sorted(source_dir.glob("*/*.htm"))
    converter = DocumentConverter()
    for source in sources:
        relative_path = source.relative_to(source_dir).with_suffix(".md")
        convert_file(source, destination_dir / relative_path, converter)
        print(f"converted {relative_path}")
    return len(sources)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("destination_dir", type=Path)
    args = parser.parse_args()
    count = convert_corpus(args.source_dir, args.destination_dir)
    print(f"converted {count} filings")


if __name__ == "__main__":
    main()
