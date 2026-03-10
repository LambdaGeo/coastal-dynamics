"""
mangrove_raster_model.py — Mangrove Model for DisSModel
=======================================================
Faithful translation of mangue.lua to DisSModel + RasterBackend.
"""
from __future__ import annotations

import numpy as np
from dissmodel.geo.raster.model import RasterModel
from dissmodel.geo.raster.backend import RasterBackend

from coastal_dynamics.common.constants import (
    MANGUE,
    MANGUE_MIGRADO,
    VEGETACAO_TERRESTRE,
    SOLO_DESCOBERTO,
    USOS_INUNDADOS,
    SOLO_MANGUE,
    SOLO_MANGUE_MIGRADO,
    SOLO_CANAL_FLUVIAL,
)


class MangroveModel(RasterModel):
    """
    Mangrove model (mangue.lua) → DisSModel + RasterBackend.

    Parameters
    ----------
    backend       : RasterBackend containing arrays "uso", "alt", and "solo"
    taxa_elevacao : meters/year — IPCC RCP8.5 ≈ 0.011
    altura_mare   : base tidal influence height (AIM) in meters. Default: 6.0
    acrecao_ativa : enables sediment accretion (Alongi 2008). Default: False
    """

    SOIL_SOURCES = [SOLO_MANGUE, SOLO_MANGUE_MIGRADO, SOLO_CANAL_FLUVIAL]
    MANGROVE_SOILS = [SOLO_MANGUE, SOLO_MANGUE_MIGRADO]

    USE_SOURCES = [MANGUE, MANGUE_MIGRADO]
    USE_TARGETS = [VEGETACAO_TERRESTRE, SOLO_DESCOBERTO]

    COEF_A, COEF_B = 1.693, 0.939  # Alongi 2008

    def setup(
        self,
        backend: RasterBackend,
        taxa_elevacao: float = 0.011,
        altura_mare: float = 6.0,
        acrecao_ativa: bool = False,
    ) -> None:
        super().setup(backend)
        self.taxa_elevacao = taxa_elevacao
        self.altura_mare = altura_mare
        self.acrecao_ativa = acrecao_ativa

        # metrics
        self.mangrove_migrated = 0
        self.soil_migrated = 0

    def execute(self) -> None:
        nivel_mar = self.env.now() * self.taxa_elevacao
        zi = self.altura_mare + nivel_mar
        taxa_ac = self.COEF_A / 1000.0 + self.COEF_B * nivel_mar

        uso_past = self.backend.get("uso").copy()
        alt_past = self.backend.get("alt").copy()
        solo_past = self.backend.get("solo").copy()

        # ── soil migration ───────────────────────────────────────────────────
        eh_fonte_solo = np.isin(solo_past, self.SOIL_SOURCES)
        solo_novo = solo_past.copy()

        for dr, dc in self.dirs:
            fonte_viz = self.shift(eh_fonte_solo.astype(np.int8), dr, dc) > 0

            cond = (
                fonte_viz
                & np.isin(uso_past, self.USE_TARGETS)
                & (solo_past != SOLO_MANGUE_MIGRADO)
                & (alt_past <= zi)
            )

            solo_novo = np.where(cond, SOLO_MANGUE_MIGRADO, solo_novo)

        # ── land-use migration — uses solo_past (faithful to TerraME .past) ──
        eh_fonte_uso = np.isin(uso_past, self.USE_SOURCES)
        uso_novo = uso_past.copy()

        for dr, dc in self.dirs:
            fonte_viz = self.shift(eh_fonte_uso.astype(np.int8), dr, dc) > 0

            cond = (
                fonte_viz
                & np.isin(uso_past, self.USE_TARGETS)
                & np.isin(solo_past, self.MANGROVE_SOILS)
                & (alt_past <= zi)
            )

            uso_novo = np.where(cond, MANGUE_MIGRADO, uso_novo)

        # ── sediment accretion (disabled by default) ─────────────────────────
        if self.acrecao_ativa:
            cond_ac = (
                np.isin(solo_past, self.MANGROVE_SOILS)
                & ~np.isin(uso_past, USOS_INUNDADOS)
            )

            self.backend.arrays["alt"] = np.where(
                cond_ac,
                alt_past + taxa_ac,
                alt_past,
            )

        self.backend.arrays["uso"] = uso_novo
        self.backend.arrays["solo"] = solo_novo

        # metrics
        self.mangrove_migrated = int(np.sum(uso_novo == MANGUE_MIGRADO))
        self.soil_migrated = int(np.sum(solo_novo == SOLO_MANGUE_MIGRADO))