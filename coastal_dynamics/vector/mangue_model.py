"""
mangrove_vector_model.py — Mangrove Model (GeoDataFrame version)
=================================================================

Vector-based version of MangroveModel using GeoDataFrame + SpatialModel,
designed for direct comparison with the NumPy implementation
(mangrove_raster_model.py).

Same logic, different substrate:

    mangrove_raster_model.py     RasterBackend (NumPy, vectorized)
    mangrove_vector_model.py  ←  GeoDataFrame (libpysal, cell-by-cell)

Three processes per step — order identical to the Lua model and the
raster implementation:

    1. migrateSoils   — propagates mangrove substrate
    2. migrateUses    — propagates MANGUE_MIGRADO land use (uses solo_past)
    3. applyAccretion — increases elevation (Alongi 2008, disabled by default)

CRITICAL NOTE: migrateUses uses solo_past — consistent with the .past
semantics used in TerraME.

Usage
-----
    from dissmodel.core import Environment
    from coastal_dynamics.vector.mangrove_vector_model import MangroveVectorModel
    import geopandas as gpd

    gdf = gpd.read_file("flood_model.shp")
    env = Environment(start_time=1, end_time=88)
    MangroveVectorModel(gdf=gdf, taxa_elevacao=0.011)
    env.run()
"""
from __future__ import annotations

import geopandas as gpd
from libpysal.weights import Queen

from dissmodel.geo.vector.model import SpatialModel
from dissmodel.visualization import track_plot

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

@track_plot("mangrove_migrated", "green")
class MangroveModel(SpatialModel):
    """
    Mangrove model implemented with DisSModel + GeoDataFrame.

    Equivalence with the raster version
    -----------------------------------
    np.isin(solo, SOURCE_SOILS)      →  solo_past.isin(SOURCE_SOILS)
    shift2d loop over DIRS_MOORE     →  loop over real GDF neighbors
    np.where(cond, new, current)     →  solo_new[idx] = SOLO_MANGUE_MIGRADO
    solo_past (not solo_new)         →  solo_past[idx] — same .past care

    Parameters
    ----------
    gdf           : GeoDataFrame with columns attr_uso, attr_alt, attr_solo
    taxa_elevacao : meters/year — IPCC RCP8.5 ≈ 0.011
    altura_mare   : base tidal influence height in meters. Default: 6.0
    acrecao_ativa : enables applyAccretion (Alongi 2008). Default: False
    attr_uso      : land-use column. Default: "uso"
    attr_alt      : elevation column. Default: "alt"
    attr_solo     : soil type column. Default: "solo"
    """

    SOURCE_SOILS  = [SOLO_MANGUE, SOLO_MANGUE_MIGRADO, SOLO_CANAL_FLUVIAL]
    MANGROVE_SOILS = [SOLO_MANGUE, SOLO_MANGUE_MIGRADO]
    SOURCE_USES   = [MANGUE, MANGUE_MIGRADO]
    TARGET_USES   = [VEGETACAO_TERRESTRE, SOLO_DESCOBERTO]

    COEF_A, COEF_B = 1.693, 0.939   # Alongi 2008

    def setup(
        self,
        taxa_elevacao: float = 0.011,
        altura_mare:   float = 6.0,
        acrecao_ativa: bool  = False,
        attr_uso:      str   = "uso",
        attr_alt:      str   = "alt",
        attr_solo:     str   = "solo",
    ) -> None:
        self.taxa_elevacao = taxa_elevacao
        self.altura_mare   = altura_mare
        self.acrecao_ativa = acrecao_ativa
        self.attr_uso      = attr_uso
        self.attr_alt      = attr_alt
        self.attr_solo     = attr_solo

        # metrics exposed for @track_plot / Chart
        self.mangrove_migrated = 0
        self.soil_migrated     = 0

        self.create_neighborhood(strategy=Queen, silence_warnings=True)

    def execute(self) -> None:
        nivel_mar = self.env.now() * self.taxa_elevacao
        zi        = self.altura_mare + nivel_mar
        taxa_ac   = self.COEF_A / 1000.0 + self.COEF_B * nivel_mar

        # snapshots — equivalent to cell.past[] in TerraME
        uso_past  = self.gdf[self.attr_uso].copy()
        alt_past  = self.gdf[self.attr_alt].copy()
        solo_past = self.gdf[self.attr_solo].copy()

        # ── migrateSoils ─────────────────────────────────────────────────────
        # Source: cell.past[soil] in SOURCE_SOILS
        # Target: neighbor.use  in TARGET_USES
        #         neighbor.soil != SOLO_MANGUE_MIGRADO
        #         neighbor.alt  <= influenceZone
        fontes_solo = set(
            solo_past.index[solo_past.isin(self.SOURCE_SOILS)]
        )
        solo_novo = solo_past.copy()

        for idx in self.gdf.index:
            if uso_past[idx] not in self.TARGET_USES:
                continue
            if solo_past[idx] == SOLO_MANGUE_MIGRADO:
                continue
            if alt_past[idx] > zi:
                continue
            if any(n in fontes_solo for n in self.neighs_id(idx)):
                solo_novo[idx] = SOLO_MANGUE_MIGRADO

        # ── migrateUses ──────────────────────────────────────────────────────
        # Source: cell.past[use] in SOURCE_USES
        # Target: neighbor.use  in TARGET_USES
        #         neighbor.soil in MANGROVE_SOILS ← solo_past (not solo_new)
        #         neighbor.alt  <= influenceZone
        fontes_uso = set(
            uso_past.index[uso_past.isin(self.SOURCE_USES)]
        )
        uso_novo = uso_past.copy()

        for idx in self.gdf.index:
            if uso_past[idx] not in self.TARGET_USES:
                continue
            if solo_past[idx] not in self.MANGROVE_SOILS:
                continue
            if alt_past[idx] > zi:
                continue
            if any(n in fontes_uso for n in self.neighs_id(idx)):
                uso_novo[idx] = MANGUE_MIGRADO

        # ── applyAccretion (disabled by default — commented in original Lua) ─
        if self.acrecao_ativa:
            alt_nova = alt_past.copy()
            for idx in self.gdf.index:
                if solo_past[idx] in self.MANGROVE_SOILS:
                    if uso_past[idx] not in USOS_INUNDADOS:
                        alt_nova[idx] += taxa_ac
            self.gdf[self.attr_alt] = alt_nova

        self.gdf[self.attr_uso]  = uso_novo
        self.gdf[self.attr_solo] = solo_novo

        # ── metrics ─────────────────────────────────────────────────────────
        self.mangrove_migrated = int((uso_novo  == MANGUE_MIGRADO).sum())
        self.soil_migrated     = int((solo_novo == SOLO_MANGUE_MIGRADO).sum())