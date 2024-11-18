from pydantic import BaseModel, field_validator
from typing import Optional


class DataFilterConfig(BaseModel):
    min_latitude: int = -90
    max_latitude: int = 90
    min_longitude: int = -180
    max_longitude: int = 180
    min_depth: int = 0
    max_depth: Optional[int] = None

    @field_validator("min_latitude", "max_latitude")
    def validate_latitude(cls, value):
        if value < -90 or value > 90:
            raise ValueError("La latitude doit être comprise entre -90 et 90.")

        return value

    @field_validator("min_longitude", "max_longitude")
    def validate_longitude(cls, value):
        if value < -180 or value > 180:
            raise ValueError("La longitude doit être comprise entre -180 et 180.")

        return value

    @field_validator("min_depth", "max_depth")
    def validate_depth(cls, value):
        if value < 0:
            raise ValueError("La profondeur doit être supérieure ou égale à 0.")

        return value