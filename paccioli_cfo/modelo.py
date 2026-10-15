"""Modelo de datos: todo estado de cuenta se convierte en una lista de Movimiento."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


@dataclass
class Movimiento:
    fuente: str                 # banco o archivo de origen
    fecha: str                  # ISO AAAA-MM-DD cuando se conoce el anio; si no, tal como viene
    descripcion: str
    cargo: float = 0.0          # sale dinero
    abono: float = 0.0          # entra dinero
    codigo: str = ""
    referencia: str = ""
    contraparte: str = ""
    categoria: str = ""
    regla: str = ""             # que regla lo clasifico (auto, tuya, sin regla)
    extra: dict = field(default_factory=dict)

    @property
    def importe(self) -> float:
        return round(self.abono - self.cargo, 2)

    @property
    def mes(self) -> str:
        return self.fecha[:7] if len(self.fecha) >= 7 and self.fecha[4] == "-" else "sin-fecha"

    @property
    def id(self) -> str:
        base = f"{self.fuente}|{self.fecha}|{self.cargo}|{self.abono}|{self.descripcion}|{self.extra.get('n', 0)}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        d["mes"] = self.mes
        d["importe"] = self.importe
        return d
