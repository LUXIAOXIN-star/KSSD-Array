#!/usr/bin/env python3
"""Core parsers and statistics for the corrected Supplementary Table S2."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
from itertools import zip_longest
import math
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.stats import binom_test


METHODS = ("Original Minimap2", "KSSD-Array")
METHOD_TOKENS = {"Original Minimap2": "original", "KSSD-Array": "kssd-array"}
PRIMARY_EXCLUDE_FLAGS = 0x100 | 0x800
HISTORICAL_EXCLUDE_FLAGS = 0x4 | 0x100 | 0x800


@dataclass(frozen=True)
class TruthRecord:
    qname: str
    reference: str
    strand_offset0: int
    strand: str
    reference_span: int
    read_length: int
    reference_length: int
    start0: int
    end0: int

    @property
    def sam_position1(self) -> int:
        return self.start0 + 1


@dataclass(frozen=True)
class Assignment:
    reference: str
    position1: int
    strand: str
    mapq: int
    flag: int
    cigar: str


@dataclass
class BamAudit:
    assignments: Dict[str, Assignment]
    primary_unmapped_seen: Set[str]
    secondary_records: int
    supplementary_records: int
    unknown_primary_queries: Set[str]
    duplicate_mapped_primary_queries: Set[str]
    total_records: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, size: int, digest: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != size:
        raise RuntimeError("size mismatch for {}: {} != {}".format(path, path.stat().st_size, size))
    observed = sha256_file(path)
    if observed != digest:
        raise RuntimeError("SHA-256 mismatch for {}: {} != {}".format(path, observed, digest))


def normalize_qname(qname: str, truth_names: object) -> str:
    if qname in truth_names:
        return qname
    if qname.endswith("/1") or qname.endswith("/2"):
        trimmed = qname[:-2]
        if trimmed in truth_names:
            return trimmed
    return qname


def iter_fastq_names(path: Path) -> Iterator[str]:
    with path.open("rt", encoding="utf-8") as handle:
        while True:
            header = handle.readline()
            if not header:
                return
            sequence = handle.readline()
            plus = handle.readline()
            quality = handle.readline()
            if not sequence or not plus or not quality or not header.startswith("@") or not plus.startswith("+"):
                raise RuntimeError("malformed FASTQ record in {}".format(path))
            if len(sequence.rstrip("\r\n")) != len(quality.rstrip("\r\n")):
                raise RuntimeError("FASTQ sequence/quality length mismatch in {}".format(path))
            yield header[1:].strip().split()[0]


def iter_truth_tsv(path: Path) -> Iterator[Tuple[str, str, int]]:
    with path.open("rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) >= 3:
                qname, reference, raw_position = fields[:3]
            elif len(fields) == 2 and ":" in fields[1]:
                qname = fields[0]
                reference, raw_position = fields[1].rsplit(":", 1)
            else:
                raise RuntimeError("unsupported truth TSV schema at {}:{}".format(path, line_number))
            yield qname, reference, int(raw_position)


def parse_aln_header(path: Path) -> Tuple[int, Dict[str, int]]:
    read_length = None
    reference_lengths: Dict[str, int] = {}
    with path.open("rt", encoding="utf-8") as handle:
        first = handle.readline().rstrip("\r\n")
        fields = first.split("\t")
        if len(fields) < 3 or fields[0] != "##ART_Illumina" or fields[1] != "read_length":
            raise RuntimeError("unexpected ART ALN header: {}".format(path))
        read_length = int(fields[2])
        for line in handle:
            line = line.rstrip("\r\n")
            if line.startswith("@SQ\t"):
                parts = line.split("\t")
                # ART preserves the full FASTA description in this field,
                # while body records and SAM use the first whitespace token.
                reference_id = parts[1].split()[0]
                reference_lengths[reference_id] = int(parts[-1])
            elif line.startswith("##Header End"):
                break
        else:
            raise RuntimeError("ART ALN header terminator missing: {}".format(path))
    return read_length, reference_lengths


def iter_aln_records(path: Path) -> Iterator[Tuple[str, str, int, str, int, int]]:
    read_length, reference_lengths = parse_aln_header(path)
    with path.open("rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("##Header End"):
                break
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            if not line.startswith(">"):
                raise RuntimeError("expected ART record header in {} body line {}".format(path, line_number))
            fields = line[1:].rstrip("\r\n").split("\t")
            if len(fields) != 4:
                raise RuntimeError("unexpected ART record schema in {}".format(path))
            reference, qname, raw_offset, strand = fields
            if strand not in ("+", "-") or reference not in reference_lengths:
                raise RuntimeError("invalid ART record metadata for {}".format(qname))
            reference_aligned = handle.readline().rstrip("\r\n")
            read_aligned = handle.readline().rstrip("\r\n")
            if not reference_aligned or not read_aligned:
                raise RuntimeError("truncated ART record for {}".format(qname))
            reference_span = len(reference_aligned.replace("-", ""))
            if reference_span <= 0:
                raise RuntimeError("empty ART reference span for {}".format(qname))
            yield qname, reference, int(raw_offset), strand, reference_span, reference_lengths[reference]


def load_truth_records(truth_tsv: Path, truth_aln: Path, read_length: int) -> Dict[str, TruthRecord]:
    aln_read_length, _ = parse_aln_header(truth_aln)
    if aln_read_length != read_length:
        raise RuntimeError("ART read-length mismatch: {} != {}".format(aln_read_length, read_length))
    truth: Dict[str, TruthRecord] = {}
    for tsv_row, aln_row in zip_longest(iter_truth_tsv(truth_tsv), iter_aln_records(truth_aln)):
        if tsv_row is None or aln_row is None:
            raise RuntimeError("truth TSV and ART ALN record counts differ")
        qname, reference, strand_offset0 = tsv_row
        aqname, areference, aoffset0, strand, reference_span, reference_length = aln_row
        if (qname, reference, strand_offset0) != (aqname, areference, aoffset0):
            raise RuntimeError("truth TSV/ART ALN mismatch: {} versus {}".format(tsv_row, aln_row[:3]))
        if qname in truth:
            raise RuntimeError("duplicate truth query: {}".format(qname))
        if strand == "+":
            start0 = strand_offset0
            end0 = start0 + reference_span
        else:
            end0 = reference_length - strand_offset0
            start0 = end0 - reference_span
        if start0 < 0 or end0 > reference_length or start0 >= end0:
            raise RuntimeError("invalid reconstructed interval for {}".format(qname))
        truth[qname] = TruthRecord(
            qname=qname, reference=reference, strand_offset0=strand_offset0,
            strand=strand, reference_span=reference_span, read_length=read_length,
            reference_length=reference_length, start0=start0, end0=end0,
        )
    return truth


def verify_fastq_truth_names(fastq: Path, truth: Dict[str, TruthRecord]) -> int:
    count = 0
    seen: Set[str] = set()
    for fastq_name, truth_name in zip_longest(iter_fastq_names(fastq), truth):
        if fastq_name is None or truth_name is None:
            raise RuntimeError("FASTQ and truth counts differ: {}".format(fastq))
        if fastq_name != truth_name:
            raise RuntimeError("FASTQ/truth order or name mismatch: {} != {}".format(fastq_name, truth_name))
        if fastq_name in seen:
            raise RuntimeError("duplicate FASTQ query: {}".format(fastq_name))
        seen.add(fastq_name)
        count += 1
    return count


def bed_reference_names(path: Path) -> Tuple[Set[str], int]:
    names: Set[str] = set()
    count = 0
    with path.open("rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 3:
                raise RuntimeError("malformed BED at {}:{}".format(path, line_number))
            start, end = int(fields[1]), int(fields[2])
            if start < 0 or end <= start:
                raise RuntimeError("invalid BED interval at {}:{}".format(path, line_number))
            names.add(fields[0])
            count += 1
    return names, count


def compute_repeat_membership(
    truth: Dict[str, TruthRecord], repeat_bed: Path, temporary_directory: Path
) -> Set[str]:
    temporary_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wt", encoding="utf-8", dir=str(temporary_directory),
        prefix="truth-origin-", suffix=".bed", delete=True,
    ) as truth_bed:
        for record in truth.values():
            truth_bed.write("{}\t{}\t{}\t{}\t0\t{}\n".format(
                record.reference, record.start0, record.end0, record.qname, record.strand
            ))
        truth_bed.flush()
        process = subprocess.Popen(
            ["bedtools", "intersect", "-a", truth_bed.name, "-b", str(repeat_bed), "-u"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        members: Set[str] = set()
        for line in process.stdout:
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 4:
                raise RuntimeError("malformed bedtools output")
            if fields[3] in members:
                raise RuntimeError("bedtools -u returned duplicate truth query")
            members.add(fields[3])
        process.stdout.close()
        stderr = process.stderr.read() if process.stderr is not None else ""
        if process.stderr is not None:
            process.stderr.close()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError("bedtools intersect failed: {}".format(stderr))
    if not members.issubset(truth):
        raise RuntimeError("repeat membership contains a non-truth query")
    return members


def sam_records(path: Path) -> Iterator[List[str]]:
    process = subprocess.Popen(
        ["samtools", "view", str(path)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    for line in process.stdout:
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) < 11:
            raise RuntimeError("malformed SAM record from {}".format(path))
        yield fields
    process.stdout.close()
    stderr = process.stderr.read() if process.stderr is not None else ""
    if process.stderr is not None:
        process.stderr.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError("samtools view failed for {}: {}".format(path, stderr))


def load_primary_assignments(path: Path, truth: Dict[str, TruthRecord]) -> BamAudit:
    assignments: Dict[str, Assignment] = {}
    primary_unmapped: Set[str] = set()
    unknown: Set[str] = set()
    duplicates: Set[str] = set()
    secondary = supplementary = total = 0
    for fields in sam_records(path):
        total += 1
        flag = int(fields[1])
        if flag & 0x100:
            secondary += 1
        if flag & 0x800:
            supplementary += 1
        if flag & PRIMARY_EXCLUDE_FLAGS:
            continue
        normalized = normalize_qname(fields[0], truth)
        if normalized not in truth:
            unknown.add(normalized)
            continue
        if flag & 0x4:
            primary_unmapped.add(normalized)
            continue
        if normalized in assignments:
            duplicates.add(normalized)
            continue
        assignments[normalized] = Assignment(
            reference=fields[2], position1=int(fields[3]),
            strand="-" if flag & 0x10 else "+", mapq=int(fields[4]),
            flag=flag, cigar=fields[5],
        )
    return BamAudit(
        assignments=assignments, primary_unmapped_seen=primary_unmapped,
        secondary_records=secondary, supplementary_records=supplementary,
        unknown_primary_queries=unknown, duplicate_mapped_primary_queries=duplicates,
        total_records=total,
    )


def strict_error_category(
    truth: TruthRecord, assignment: Optional[Assignment], tolerance: int
) -> str:
    if assignment is None:
        return "unmapped_or_no_primary"
    if assignment.reference != truth.reference:
        return "wrong_reference"
    if assignment.strand != truth.strand:
        return "wrong_strand"
    if abs(assignment.position1 - truth.sam_position1) > tolerance:
        return "wrong_position"
    return "correct"


def historical_compatible_correct(
    truth: TruthRecord, assignment: Optional[Assignment], tolerance: int
) -> bool:
    if assignment is None or assignment.reference != truth.reference:
        return False
    first = truth.strand_offset0
    second = truth.strand_offset0 - (truth.read_length - 1)
    return abs(assignment.position1 - first) <= tolerance or abs(assignment.position1 - second) <= tolerance


def historical_bam_metrics(
    path: Path, truth: Dict[str, TruthRecord], tolerance: int
) -> Dict[str, int]:
    primary = correct = mapq60 = unknown = duplicates = 0
    seen: Set[str] = set()
    for fields in sam_records(path):
        flag = int(fields[1])
        if flag & HISTORICAL_EXCLUDE_FLAGS:
            continue
        primary += 1
        qname = normalize_qname(fields[0], truth)
        if qname not in truth:
            unknown += 1
            continue
        if qname in seen:
            duplicates += 1
        seen.add(qname)
        record = truth[qname]
        assignment = Assignment(
            reference=fields[2], position1=int(fields[3]),
            strand="-" if flag & 0x10 else "+", mapq=int(fields[4]),
            flag=flag, cigar=fields[5],
        )
        if historical_compatible_correct(record, assignment, tolerance):
            correct += 1
        if assignment.mapq == 60:
            mapq60 += 1
    return {
        "truth_matched_primary": primary - unknown,
        "correct": correct,
        "mapq60": mapq60,
        "unknown": unknown,
        "duplicate_primary": duplicates,
    }


def paired_cells(original: Sequence[bool], kssd: Sequence[bool]) -> Tuple[int, int, int, int]:
    if len(original) != len(kssd):
        raise ValueError("paired vectors differ in length")
    both = original_only = kssd_only = neither = 0
    for left, right in zip(original, kssd):
        if left and right:
            both += 1
        elif left:
            original_only += 1
        elif right:
            kssd_only += 1
        else:
            neither += 1
    return both, original_only, kssd_only, neither


def bootstrap_paired_delta(
    cells: Tuple[int, int, int, int], iterations: int, seed: int
) -> Tuple[float, float]:
    total = sum(cells)
    if total <= 0:
        raise ValueError("bootstrap denominator is zero")
    probabilities = np.asarray(cells, dtype=float) / float(total)
    draws = np.random.RandomState(seed).multinomial(total, probabilities, size=iterations)
    deltas = 100.0 * (draws[:, 2] - draws[:, 1]) / float(total)
    lower, upper = np.percentile(deltas, [2.5, 97.5])
    return float(lower), float(upper)


def exact_mcnemar_p(original_only: int, kssd_only: int) -> float:
    discordant = original_only + kssd_only
    if discordant == 0:
        return 1.0
    return float(binom_test(min(original_only, kssd_only), discordant, 0.5, alternative="two-sided"))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    with path.open("wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)
