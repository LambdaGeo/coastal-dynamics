"""
flood_raster_model.py — Hydrological Model for DisSModel
========================================================
Faithful translation of hidro.lua to DisSModel + RasterBackend.
"""
from __future__ import annotations

import numpy as np
from dissmodel.geo.raster.model import RasterModel
from dissmodel.geo.raster.backend import RasterBackend

from coastal_dynamics.common.constants import (
    USOS_INUNDADOS,
    REGRAS_INUNDACAO,
    MAR,
)


class FloodModel(RasterModel):
    """
    Hydrological model (hidro.lua) → DisSModel + RasterBackend.

    Parameters
    ----------
    backend       : RasterBackend containing arrays "uso" and "alt"
    taxa_elevacao : meters/year — IPCC RCP8.5 ≈ 0.011
    aim_base      : base tidal influence height in meters. Default: 6.0
    """

    def setup(
        self,
        backend:       RasterBackend,
        taxa_elevacao: float = 0.011,
        aim_base:      float = 6.0,
    ) -> None:
        super().setup(backend)
        self.taxa_elevacao = taxa_elevacao
        self.aim_base      = aim_base

        # metrics exposed for charts / tracking
        self.flooded_cells = 0
        self.newly_flooded = 0
        self.current_sea_level = 0.0

    def execute(self) -> None:
        nivel_mar  = self.env.now() * self.taxa_elevacao
        rows, cols = self.shape

        uso_past = self.backend.get("uso").copy()
        alt_past = self.backend.get("alt").copy()

        # source cells: already flooded or sea
        eh_fonte = np.isin(uso_past, USOS_INUNDADOS) & (alt_past >= 0)

        viz_baixos = np.ones((rows, cols), dtype=float)
        for dr, dc in self.dirs:
            viz_baixos += (self.shift(alt_past, dr, dc) <= alt_past).astype(float)

        fluxo     = np.where(eh_fonte, self.taxa_elevacao / viz_baixos, 0.0)
        delta_alt = fluxo.copy()
        uso_novo  = uso_past.copy()

        for dr, dc in self.dirs:
            fonte_viz = self.shift(eh_fonte.astype(float), dr, dc) > 0
            alt_viz   = self.shift(alt_past, dr, dc)
            fluxo_viz = self.shift(fluxo, dr, dc)

            # 1. elevation update — relative condition
            delta_alt += np.where(
                fonte_viz & (alt_past <= alt_viz), fluxo_viz, 0.0
            )

            # 2. flooding — absolute elevation threshold
            for uso_seco, uso_inund in REGRAS_INUNDACAO.items():
                pode = fonte_viz & (uso_past == uso_seco) & (alt_past <= nivel_mar)
                uso_novo = np.where(pode, uso_inund, uso_novo)

        self.backend.arrays["alt"] = alt_past + delta_alt
        self.backend.arrays["uso"] = uso_novo

        # metrics
        inund = np.isin(uso_novo, USOS_INUNDADOS) & (uso_novo != MAR)
        novas = np.isin(uso_novo, USOS_INUNDADOS) & ~np.isin(uso_past, USOS_INUNDADOS)

        self.flooded_cells     = int(np.sum(inund))
        self.newly_flooded     = int(np.sum(novas))
        self.current_sea_level = round(nivel_mar, 4)