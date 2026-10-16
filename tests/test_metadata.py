"""Metadata validation gate for the qompassai/debian repository.

This repo ships configuration and documentation for Debian servers;
its machine-checkable contract is the publication metadata set
(.zenodo.json, CITATION.cff, citation.bib, .github/FUNDING.yml and
LICENSE). These tests validate the real files (validation cases)
and prove the checks reject corrupted metadata (adversarial cases),
so a future edit that breaks the set fails here instead of at
Zenodo or on a citation.

Run: python3 -m pytest tests/ -q   (requires PyYAML)
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = 'https://github.com/qompassai/debian'
EXPECTED_LICENSE = 'Apache-2.0'
MAX_FILE_BYTES = 1_000_000
ORCID_RE = re.compile(r'^(https://orcid\.org/)?\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')


def _read_text(name: str) -> str:
    """Read one repo file, bounded, as UTF-8 text."""
    path = REPO_ROOT / name
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise AssertionError(f'{name}: {len(data)} bytes exceeds {MAX_FILE_BYTES}')
    return data.decode('utf-8')


def _validate_zenodo(data: object) -> list[str]:
    """Return the list of contract violations in parsed .zenodo.json data."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ['zenodo: top level is not an object']
    if not isinstance(data.get('title'), str) or not data['title']:
        problems.append('zenodo: title missing or empty')
    if data.get('license') != EXPECTED_LICENSE:
        problems.append(
            f'zenodo: license is {data.get("license")!r}, want {EXPECTED_LICENSE}'
        )
    if data.get('upload_type') != 'software':
        problems.append("zenodo: upload_type is not 'software'")
    creators = data.get('creators')
    if not isinstance(creators, list) or not creators:
        problems.append('zenodo: creators missing or empty')
        return problems
    orcids = [c.get('orcid') for c in creators if isinstance(c, dict)]
    if not any(isinstance(o, str) and ORCID_RE.match(o) for o in orcids):
        problems.append('zenodo: no creator carries a well-formed ORCID')
    identifiers = data.get('related_identifiers') or []
    urls = [i.get('identifier') for i in identifiers if isinstance(i, dict)]
    if REPO_URL not in urls:
        problems.append('zenodo: related_identifiers do not reference the repo URL')
    return problems


def _validate_citation(data: object) -> list[str]:
    """Return the list of contract violations in parsed CITATION.cff data."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ['citation: top level is not a mapping']
    if data.get('cff-version') != '1.2.0':
        problems.append(
            f"citation: cff-version is {data.get('cff-version')!r}, want '1.2.0'"
        )
    if data.get('license') != EXPECTED_LICENSE:
        problems.append(
            f'citation: license is {data.get("license")!r}, want {EXPECTED_LICENSE}'
        )
    if data.get('repository-code') != REPO_URL:
        problems.append('citation: repository-code does not match the repo URL')
    authors = data.get('authors')
    if not isinstance(authors, list) or not authors:
        problems.append('citation: authors missing or empty')
    elif not all(
        isinstance(a, dict) and a.get('family-names') and a.get('given-names')
        for a in authors
    ):
        problems.append('citation: every author needs family-names and given-names')
    return problems


def _validate_bibtex(text: str) -> list[str]:
    """Return the list of contract violations in citation.bib text."""
    problems: list[str] = []
    if not text.lstrip().startswith('@'):
        problems.append('bibtex: does not start with an entry')
    if text.count('{') != text.count('}'):
        problems.append('bibtex: unbalanced braces')
    if REPO_URL not in text:
        problems.append('bibtex: does not reference the repo URL')
    return problems


def _zenodo() -> object:
    return json.loads(_read_text('.zenodo.json'))


def _citation() -> object:
    return yaml.safe_load(_read_text('CITATION.cff'))


# --- Validation: the shipped files satisfy the contract. ---


def test_zenodo_metadata_is_valid() -> None:
    assert _validate_zenodo(_zenodo()) == []


def test_citation_metadata_is_valid() -> None:
    assert _validate_citation(_citation()) == []


def test_funding_file_is_valid_yaml_with_github() -> None:
    data = yaml.safe_load(_read_text('.github/FUNDING.yml'))
    assert isinstance(data, dict)
    assert isinstance(data.get('github'), str) and data['github']


def test_bibtex_is_valid() -> None:
    assert _validate_bibtex(_read_text('citation.bib')) == []


def test_license_file_is_apache_2() -> None:
    text = _read_text('LICENSE')
    assert 'Apache License' in text
    assert 'Version 2.0' in text


def test_zenodo_and_citation_licenses_agree() -> None:
    zenodo = _zenodo()
    citation = _citation()
    assert isinstance(zenodo, dict) and isinstance(citation, dict)
    assert zenodo['license'] == citation['license'] == EXPECTED_LICENSE


# --- Adversarial: corrupted metadata must be rejected. ---


def test_zenodo_wrong_license_is_rejected() -> None:
    data = copy.deepcopy(_zenodo())
    assert isinstance(data, dict)
    data['license'] = 'MIT'
    assert _validate_zenodo(data) != []


def test_zenodo_missing_title_is_rejected() -> None:
    data = copy.deepcopy(_zenodo())
    assert isinstance(data, dict)
    del data['title']
    assert _validate_zenodo(data) != []


def test_zenodo_malformed_orcid_is_rejected() -> None:
    data = copy.deepcopy(_zenodo())
    assert isinstance(data, dict)
    for creator in data['creators']:
        creator.pop('orcid', None)
    data['creators'][0]['orcid'] = 'not-an-orcid'
    assert _validate_zenodo(data) != []


def test_zenodo_wrong_repo_link_is_rejected() -> None:
    data = copy.deepcopy(_zenodo())
    assert isinstance(data, dict)
    data['related_identifiers'] = [
        {
            'identifier': 'https://github.com/qompassai/other',
            'relation': 'isSupplementTo',
        }
    ]
    assert _validate_zenodo(data) != []


def test_citation_wrong_license_is_rejected() -> None:
    data = copy.deepcopy(_citation())
    assert isinstance(data, dict)
    data['license'] = 'GPL-3.0'
    assert _validate_citation(data) != []


def test_citation_author_without_names_is_rejected() -> None:
    data = copy.deepcopy(_citation())
    assert isinstance(data, dict)
    data['authors'] = [{'affiliation': 'Qompass AI'}]
    assert _validate_citation(data) != []


def test_bibtex_unbalanced_braces_are_rejected() -> None:
    assert _validate_bibtex('@software{x, title = {oops}') != []


def test_non_mapping_metadata_is_rejected() -> None:
    assert _validate_zenodo(['not', 'a', 'dict']) != []
    assert _validate_citation('just a string') != []
