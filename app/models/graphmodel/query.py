from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import neo4j
from neo4j import Query
from neo4j.exceptions import ClientError, CypherTypeError

NODE_PROPERTIES_QUERY = (
    "CALL apoc.meta.data() "
    "YIELD label, other, elementType, type, property "
    "WHERE NOT type = 'RELATIONSHIP' AND elementType = 'node' "
    "AND NOT label IN $EXCLUDED_LABELS "
    "WITH label AS nodeLabel, collect({property:property, type:type}) AS properties "
    "RETURN {label: nodeLabel, properties: properties} AS output"
)

REL_PROPERTIES_QUERY = (
    "CALL apoc.meta.data() "
    "YIELD label, other, elementType, type, property "
    "WHERE NOT type = 'RELATIONSHIP' AND elementType = 'relationship' "
    "AND NOT label in $EXCLUDED_LABELS "
    "WITH label AS relType, collect({property:property, type:type}) AS properties "
    "RETURN {type: relType, properties: properties} AS output"
)

REL_QUERY = (
    "CALL apoc.meta.data() "
    "YIELD label, other, elementType, type, property "
    "WHERE type = 'RELATIONSHIP' AND elementType = 'node' "
    "UNWIND other AS other_node "
    "WITH * WHERE NOT label IN $EXCLUDED_LABELS "
    "AND NOT other_node IN $EXCLUDED_LABELS "
    "RETURN {start: label, type: property, end: toString(other_node)} AS output"
)

INDEX_QUERY = (
    "CALL apoc.schema.nodes() YIELD label, properties, type, size, valuesSelectivity "
    "WHERE type = 'RANGE' RETURN *, "
    "size * valuesSelectivity as distinctValues"
)

SCHEMA_COUNTS_QUERY = (
    "CALL apoc.meta.graph({sample: 1000, maxRels: 100}) "
    "YIELD nodes, relationships "
    "RETURN nodes, [rel in relationships | {name:apoc.any.property"
    "(rel, 'type'), count: apoc.any.property(rel, 'count')}]"
    " AS relationships"
)
