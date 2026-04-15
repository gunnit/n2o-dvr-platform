"""Dispatcher routes every tipo_documento to the right class."""

import uuid

import pytest

from app.services.document_generator.dispatcher import (
    ALL_DOCUMENT_TYPES,
    get_generator_for,
)


def test_all_17_tipi_map_to_distinct_classes():
    instances = {}
    az_id = uuid.uuid4()
    for tipo in ALL_DOCUMENT_TYPES:
        gen = get_generator_for(tipo, az_id, db=None)
        assert gen is not None
        instances[tipo] = type(gen).__name__
    # All 17 distinct
    assert len(set(instances.values())) == 17


def test_dispatcher_case_insensitive():
    az_id = uuid.uuid4()
    upper = get_generator_for("DVR_MASTER", az_id, db=None)
    lower = get_generator_for("dvr_master", az_id, db=None)
    dashed = get_generator_for("dvr-master", az_id, db=None)
    assert type(upper).__name__ == type(lower).__name__ == type(dashed).__name__


def test_unknown_tipo_raises():
    with pytest.raises(ValueError):
        get_generator_for("UNKNOWN_DOC", uuid.uuid4(), db=None)
