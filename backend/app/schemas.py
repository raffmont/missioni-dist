import enum
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Status


class TransportMode(str, enum.Enum):
    AIRPLANE = "Aereo"
    TRAIN = "Treno"
    RENTAL_CAR = "Auto a noleggio"
    PERSONAL_CAR = "Auto personale"
    DEPARTMENT_CAR = "Auto dipartimentale"


class MissionFields(BaseModel):
    destination: str = Field(min_length=2, max_length=160)
    country: str = Field(default="Italia", min_length=2, max_length=80)
    purpose: str = Field(min_length=5, max_length=2000)
    fund_code: str = Field(min_length=1, max_length=80)
    cup: str | None = Field(default=None, max_length=40)
    fund_manager: str = Field(min_length=2, max_length=120)
    planned_start: date
    planned_end: date

    @field_validator("planned_start", "planned_end", mode="before")
    @classmethod
    def date_only(cls, value):
        if isinstance(value, datetime) or (
            isinstance(value, str) and ("T" in value or " " in value)
        ):
            raise ValueError("Inserire una data senza orario o fuso orario")
        return value

    @model_validator(mode="after")
    def dates(self):
        if self.planned_end <= self.planned_start:
            raise ValueError("La fine deve seguire l'inizio")
        return self


class MissionIn(MissionFields):
    transport_modes: list[TransportMode] | None = Field(default=None, min_length=1, max_length=5)
    # Deprecated input retained for existing clients during Sprint A.
    transport_mode: TransportMode | None = None

    @model_validator(mode="after")
    def transports(self):
        selected = self.transport_modes or (
            [self.transport_mode] if self.transport_mode is not None else []
        )
        if not selected:
            raise ValueError("Selezionare almeno un mezzo di trasporto")
        self.transport_modes = list(dict.fromkeys(selected))
        self.transport_mode = self.transport_modes[0]
        return self


class MissionPatch(MissionIn):
    pass


class MissionOut(MissionFields):
    model_config = ConfigDict(from_attributes=True)
    transport_modes: list[str]
    # Deprecated compatibility projection: first selected mode.
    transport_mode: str
    id: str
    requester_id: str
    status: Status
    version: int


class ProtocolIn(BaseModel):
    protocol_number: str = Field(min_length=1, max_length=80)
    protocol_date: date


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str


class CredentialResetIn(BaseModel):
    temporary_password: str = Field(min_length=14, max_length=128)


class DeleteAccountIn(BaseModel):
    confirmation: str
