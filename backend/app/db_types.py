from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import UserDefinedType


class GeographyPoint(UserDefinedType):
    """PostGIS geography(Point, 4326), represented as text in SQLite unit schemas."""

    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "geography(Point,4326)"


@compiles(GeographyPoint, "sqlite")
def compile_geography_point_sqlite(
    _: GeographyPoint, __: object, **___: object
) -> str:
    return "TEXT"
