"""Calibration metadata, sourced assumptions, and latent run-state sampling."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ayoe.constants import STAGE_LABELS
from ayoe.models import BeamConfig, RunLatentState


@dataclass(frozen=True, slots=True)
class CalibrationSource:
    title: str
    url: str
    source_type: str
    note: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "source_type": self.source_type,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class DistributionCalibration:
    family: str
    low: float
    high: float
    concentration: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "family": self.family,
            "low": float(self.low),
            "high": float(self.high),
            "concentration": float(self.concentration),
        }


@dataclass(frozen=True, slots=True)
class ParameterCalibration:
    key: str
    label: str
    baseline: float
    units: str
    confidence: str
    source_classification: str
    rationale: str
    tunable: bool
    distribution: DistributionCalibration
    sources: tuple[CalibrationSource, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "baseline": float(self.baseline),
            "units": self.units,
            "confidence": self.confidence,
            "source_classification": self.source_classification,
            "rationale": self.rationale,
            "tunable": bool(self.tunable),
            "distribution": self.distribution.to_dict(),
            "sources": [source.to_dict() for source in self.sources],
        }


CALIBRATION_REGISTRY: dict[str, ParameterCalibration] = {
    "beam.proton_count": ParameterCalibration(
        key="beam.proton_count",
        label="Protons on target per cycle",
        baseline=1.25e13,
        units="protons/cycle",
        confidence="medium",
        source_classification="historical_cern_operations_plus_tunable_scaling",
        rationale=(
            "Historical CERN antiproton-source operation reported roughly 1.25e13 protons "
            "per pulse on target; the model uses this as a calibrated anchor while still "
            "treating cycle size as a tunable scenario parameter."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="lognormal",
            low=1.0e13,
            high=1.4e13,
            concentration=30.0,
        ),
        sources=(
            CalibrationSource(
                title="The CERN Antiproton Source (1983)",
                url="https://cds.cern.ch/record/146356/files/HEACC83_14-16.pdf",
                source_type="conference_paper",
                note="Table II lists 1.25×10^13 protons per pulse on target in operations.",
            ),
        ),
    ),
    "stages.proton_beam_input.nominal_efficiency": ParameterCalibration(
        key="stages.proton_beam_input.nominal_efficiency",
        label="Delivered proton-beam quality",
        baseline=0.985,
        units="survival probability",
        confidence="low",
        source_classification="engineering_estimate",
        rationale=(
            "No single public CERN source provides a direct stage efficiency for delivered beam "
            "quality in this abstraction, so the range is treated as an engineering prior around "
            "a high-availability beam-delivery regime."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.970,
            high=0.997,
            concentration=60.0,
        ),
        sources=(),
    ),
    "stages.antiproton_creation.nominal_efficiency": ParameterCalibration(
        key="stages.antiproton_creation.nominal_efficiency",
        label="Antiproton production and collection efficiency",
        baseline=8.0e-7,
        units="antiprotons per proton",
        confidence="medium",
        source_classification="sourced_range",
        rationale=(
            "Historical CERN antiproton-source operation reported about 6×10^6 to 8×10^6 "
            "antiprotons injected per pulse for ~1.25×10^13 protons on target, with an "
            "earlier design target near 2.5×10^7 per 1×10^13."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=4.5e-7,
            high=2.5e-6,
            concentration=22.0,
        ),
        sources=(
            CalibrationSource(
                title="The CERN Antiproton Source (1983)",
                url="https://cds.cern.ch/record/146356/files/HEACC83_14-16.pdf",
                source_type="conference_paper",
                note="Table II reports 6×10^6 operational and 8×10^6 best antiprotons injected per pulse.",
            ),
            CalibrationSource(
                title="Operational Experience with the ELENA Ion Source",
                url="https://cds.cern.ch/record/2778538/files/Fulltext.pdf",
                source_type="accelerator_paper",
                note="Describes the AD delivering roughly 3×10^7 antiprotons per pulse at 5.3 MeV.",
            ),
        ),
    ),
    "stages.particle_selection.nominal_efficiency": ParameterCalibration(
        key="stages.particle_selection.nominal_efficiency",
        label="Momentum-selection and transport acceptance",
        baseline=0.42,
        units="acceptance probability",
        confidence="low",
        source_classification="inferred_engineering_range",
        rationale=(
            "The public sources describe focusing, cooling, bunch rotation, collimation, and "
            "transport constraints but do not publish a single stage acceptance for this abstract "
            "selection layer, so this is an inferred range meant to capture significant transport loss."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.22,
            high=0.62,
            concentration=16.0,
        ),
        sources=(
            CalibrationSource(
                title="The Antiproton Decelerator",
                url="https://home.cern/science/accelerators/antiproton-decelerator",
                source_type="cern_overview",
                note="Only a fraction of produced antiprotons have the right energy to be injected and stored.",
            ),
        ),
    ),
    "stages.ad_survival.nominal_efficiency": ParameterCalibration(
        key="stages.ad_survival.nominal_efficiency",
        label="AD deceleration and cooling survival",
        baseline=0.78,
        units="survival probability",
        confidence="medium",
        source_classification="machine_performance_estimate",
        rationale=(
            "This stage represents survival through repeated cooling and deceleration in the AD "
            "towards 5.3 MeV; the range is calibrated as a moderately lossy but high-survival machine layer."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.62,
            high=0.90,
            concentration=30.0,
        ),
        sources=(
            CalibrationSource(
                title="The Antiproton Decelerator",
                url="https://home.cern/science/accelerators/antiproton-decelerator",
                source_type="cern_overview",
                note="Describes repeated cycles of cooling and deceleration from production to 5.3 MeV.",
            ),
        ),
    ),
    "stages.elena_survival.nominal_efficiency": ParameterCalibration(
        key="stages.elena_survival.nominal_efficiency",
        label="ELENA deceleration and delivery survival",
        baseline=0.72,
        units="survival probability",
        confidence="medium",
        source_classification="sourced_range_plus_inference",
        rationale=(
            "ELENA reduces beam energy from 5.3 MeV to 100 keV and improves trapping efficiency by "
            "10× to 100×. Public operation reports show 5×10^6 to 10×10^6 antiprotons per bunch at extraction, "
            "which anchors a moderately high but still lossy delivery stage."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.55,
            high=0.88,
            concentration=26.0,
        ),
        sources=(
            CalibrationSource(
                title="The Antiproton Decelerator",
                url="https://home.cern/science/accelerators/antiproton-decelerator",
                source_type="cern_overview",
                note="ELENA decelerates to 100 keV and increases trapped antiprotons by a factor of 10 to 100.",
            ),
            CalibrationSource(
                title="Accelerator Report: LHC protons outpacing the Easter tradition",
                url="https://home.cern/news/news/accelerators/accelerator-report-lhc-protons-outpacing-easter-tradition",
                source_type="cern_news",
                note="ELENA extracted bunches containing 10 million antiprotons in early 2025.",
            ),
            CalibrationSource(
                title="Production of antihydrogen atoms by 6 keV antiprotons interacting with positronium",
                url="https://cds.cern.ch/record/2862642/files/CERN-EP-2023-120.pdf",
                source_type="experiment_paper",
                note="GBAR reported 5×10^6 to 7×10^6 antiprotons per bunch at extraction in the 2022 run.",
            ),
        ),
    ),
    "stages.trap_capture.nominal_efficiency": ParameterCalibration(
        key="stages.trap_capture.nominal_efficiency",
        label="Low-energy antiproton trap capture",
        baseline=0.08,
        units="capture probability",
        confidence="low",
        source_classification="derived_from_public_experiment_scales",
        rationale=(
            "This stage bridges ELENA-delivered antiprotons and the smaller trapped antiproton clouds "
            "actually used in antihydrogen synthesis. The range is inferred from public ELENA bunch sizes "
            "and ALPHA mixing batches and should be read as a tunable estimate rather than a published machine number."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.03,
            high=0.16,
            concentration=12.0,
        ),
        sources=(
            CalibrationSource(
                title="ALPHA: Precision measurements on trapped antihydrogen",
                url="https://cds.cern.ch/record/2312593/files/arXiv%3A1803.10057.pdf",
                source_type="experiment_review",
                note="Describes mixing attempts using around 100,000 trapped antiprotons.",
            ),
            CalibrationSource(
                title="Accelerator Report: LHC protons outpacing the Easter tradition",
                url="https://home.cern/news/news/accelerators/accelerator-report-lhc-protons-outpacing-easter-tradition",
                source_type="cern_news",
                note="ELENA extracted bunches containing 10 million antiprotons.",
            ),
        ),
    ),
    "stages.antihydrogen_formation.nominal_efficiency": ParameterCalibration(
        key="stages.antihydrogen_formation.nominal_efficiency",
        label="Antihydrogen formation efficiency",
        baseline=0.28,
        units="atoms per trapped antiproton",
        confidence="high",
        source_classification="sourced_range",
        rationale=(
            "ALPHA publicly reported around 25,000 antihydrogen atoms from roughly 90,000 to 100,000 antiprotons "
            "per mixing attempt, placing the formation efficiency in the few-tenths range."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=0.18,
            high=0.38,
            concentration=40.0,
        ),
        sources=(
            CalibrationSource(
                title="ALPHA experiment observes the light spectrum of antimatter for the first time",
                url="https://home.cern/news/press-release/cern/alpha-experiment-observes-light-spectrum-antimatter-first-time",
                source_type="cern_press_release",
                note="Reported about 25,000 antihydrogen atoms from about 90,000 antiprotons per attempt.",
            ),
            CalibrationSource(
                title="ALPHA: Precision measurements on trapped antihydrogen",
                url="https://cds.cern.ch/record/2312593/files/arXiv%3A1803.10057.pdf",
                source_type="experiment_review",
                note="Reported about 30,000 antihydrogen atoms from around 100,000 antiprotons per mixing attempt.",
            ),
            CalibrationSource(
                title="Breakthrough in antimatter production",
                url="https://home.cern/news/news/experiments/breakthrough-antimatter-production",
                source_type="cern_news",
                note="Production rate increased eightfold with improved positron cooling, reinforcing this stage as strongly tunable.",
            ),
        ),
    ),
    "stages.final_usable_yield.nominal_efficiency": ParameterCalibration(
        key="stages.final_usable_yield.nominal_efficiency",
        label="Trappable or otherwise usable antihydrogen fraction",
        baseline=6.0e-4,
        units="usable atoms per formed antihydrogen atom",
        confidence="medium",
        source_classification="sourced_range",
        rationale=(
            "ALPHA reported trapping up to around 20 antihydrogen atoms from about 30,000 produced in a cycle, "
            "and another public result reported an average of 14 trapped anti-atoms per trial using stacked production."
        ),
        tunable=True,
        distribution=DistributionCalibration(
            family="scaled_beta",
            low=2.0e-4,
            high=1.1e-3,
            concentration=18.0,
        ),
        sources=(
            CalibrationSource(
                title="ALPHA: Precision measurements on trapped antihydrogen",
                url="https://cds.cern.ch/record/2312593/files/arXiv%3A1803.10057.pdf",
                source_type="experiment_review",
                note="Reported up to 20 trapped atoms from about 30,000 antihydrogen atoms in a production cycle.",
            ),
            CalibrationSource(
                title="ALPHA experiment observes the light spectrum of antimatter for the first time",
                url="https://home.cern/news/press-release/cern/alpha-experiment-observes-light-spectrum-antimatter-first-time",
                source_type="cern_press_release",
                note="Reported an average of 14 trapped anti-atoms per trial using stacked cycles.",
            ),
        ),
    ),
}


REGIME_LIBRARY: dict[str, dict[str, float | str]] = {
    "favourable": {
        "probability": 0.15,
        "beam_shift": 0.45,
        "cooling_shift": 0.55,
        "stability_shift": 0.40,
        "timing_shift": 0.35,
        "shock_scale": 0.70,
    },
    "nominal": {
        "probability": 0.55,
        "beam_shift": 0.00,
        "cooling_shift": 0.00,
        "stability_shift": 0.00,
        "timing_shift": 0.00,
        "shock_scale": 1.00,
    },
    "stressed": {
        "probability": 0.20,
        "beam_shift": -0.30,
        "cooling_shift": -0.35,
        "stability_shift": -0.40,
        "timing_shift": -0.25,
        "shock_scale": 1.35,
    },
    "unstable": {
        "probability": 0.10,
        "beam_shift": -0.55,
        "cooling_shift": -0.45,
        "stability_shift": -0.65,
        "timing_shift": -0.50,
        "shock_scale": 1.70,
    },
}


LATENT_CORRELATION = np.array(
    [
        [1.00, 0.42, 0.58, 0.40],
        [0.42, 1.00, 0.46, 0.36],
        [0.58, 0.46, 1.00, 0.52],
        [0.40, 0.36, 0.52, 1.00],
    ],
    dtype=float,
)


def get_parameter_calibration(key: str) -> ParameterCalibration:
    return CALIBRATION_REGISTRY[key]


def calibration_snapshot() -> dict[str, dict[str, Any]]:
    return {key: calibration.to_dict() for key, calibration in CALIBRATION_REGISTRY.items()}


def stage_calibration_snapshot(stage_name: str, center: float) -> dict[str, Any]:
    key = f"stages.{stage_name}.nominal_efficiency"
    calibration = get_parameter_calibration(key)
    low, high = scaled_calibration_bounds(calibration, center)
    payload = calibration.to_dict()
    payload.update(
        {
            "scenario_center": float(center),
            "scenario_low": float(low),
            "scenario_high": float(high),
            "stage_label": STAGE_LABELS[stage_name],
        }
    )
    return payload


def build_config_calibration_snapshot(config) -> dict[str, Any]:
    beam_calibration = get_parameter_calibration("beam.proton_count")
    return {
        "beam": {
            "proton_count": {
                **beam_calibration.to_dict(),
                "scenario_center": float(config.beam.proton_count),
            }
        },
        "stages": {
            stage_name: stage_calibration_snapshot(stage_name, config.stages[stage_name].nominal_efficiency)
            for stage_name in config.stages
        },
    }


def scaled_calibration_bounds(
    calibration: ParameterCalibration,
    scenario_center: float,
) -> tuple[float, float]:
    if calibration.baseline <= 0:
        return calibration.distribution.low, calibration.distribution.high

    scale = scenario_center / calibration.baseline
    low = calibration.distribution.low * scale
    high = calibration.distribution.high * scale

    if calibration.units.endswith("probability") or calibration.units.startswith("usable atoms"):
        low = float(np.clip(low, 0.0, 1.0))
        high = float(np.clip(high, low + 1e-12, 1.0))
    return low, high


def sample_calibrated_probability(
    calibration: ParameterCalibration,
    scenario_center: float,
    rng: np.random.Generator,
) -> float:
    low, high = scaled_calibration_bounds(calibration, scenario_center)
    if np.isclose(high, low):
        return low

    concentration = max(calibration.distribution.concentration, 2.0)
    scaled_mean = (scenario_center - low) / (high - low)
    scaled_mean = float(np.clip(scaled_mean, 1e-6, 1.0 - 1e-6))
    alpha = max(scaled_mean * concentration, 1e-3)
    beta = max((1.0 - scaled_mean) * concentration, 1e-3)
    draw = float(rng.beta(alpha, beta))
    return low + (draw * (high - low))


def sample_lognormal_around_center(
    center: float,
    low: float,
    high: float,
    rng: np.random.Generator,
) -> float:
    log_center = np.log(center)
    sigma = max((np.log(high) - np.log(low)) / 4.0, 1e-6)
    value = float(rng.lognormal(mean=log_center, sigma=sigma))
    return float(np.clip(value, low, high))


def _clamp_factor(value: float, lower: float = 0.55, upper: float = 1.45) -> float:
    return float(np.clip(value, lower, upper))


def _bounded_geometric_mean(
    values: list[float],
    lower: float = 0.55,
    upper: float = 1.45,
) -> float:
    clipped = [_clamp_factor(value, lower, upper) for value in values]
    return math.prod(clipped) ** (1.0 / len(clipped))


def sample_run_latent_state(rng: np.random.Generator) -> RunLatentState:
    regime_names = list(REGIME_LIBRARY)
    probabilities = np.array(
        [float(REGIME_LIBRARY[name]["probability"]) for name in regime_names],
        dtype=float,
    )
    probabilities /= probabilities.sum()
    regime_name = str(rng.choice(regime_names, p=probabilities))
    regime = REGIME_LIBRARY[regime_name]

    latent_draw = rng.multivariate_normal(
        mean=np.zeros(4, dtype=float),
        cov=LATENT_CORRELATION,
    )
    scale = 0.12

    beam_quality = _clamp_factor(1.0 + (scale * (latent_draw[0] + float(regime["beam_shift"]))))
    cooling_quality = _clamp_factor(
        1.0 + (scale * (latent_draw[1] + float(regime["cooling_shift"])))
    )
    system_stability = _clamp_factor(
        1.0 + (scale * (latent_draw[2] + float(regime["stability_shift"])))
    )
    timing_precision = _clamp_factor(
        1.0 + (scale * (latent_draw[3] + float(regime["timing_shift"])))
    )
    trap_readiness = _bounded_geometric_mean(
        [cooling_quality, system_stability, timing_precision],
        lower=0.60,
        upper=1.50,
    )
    formation_readiness = _bounded_geometric_mean(
        [cooling_quality, timing_precision, 0.5 * (beam_quality + system_stability)],
        lower=0.60,
        upper=1.50,
    )
    shock_pressure = _clamp_factor(
        float(regime["shock_scale"])
        * (1.0 + (0.18 * max(0.0, 1.0 - system_stability)) + (0.10 * max(0.0, 1.0 - timing_precision))),
        lower=0.65,
        upper=1.85,
    )

    return RunLatentState(
        regime_name=regime_name,
        beam_quality=beam_quality,
        cooling_quality=cooling_quality,
        system_stability=system_stability,
        timing_precision=timing_precision,
        shock_pressure=shock_pressure,
        trap_readiness=trap_readiness,
        formation_readiness=formation_readiness,
        regime_shock_scale=float(regime["shock_scale"]),
    )


def sample_run_proton_count(
    beam: BeamConfig,
    latent_state: RunLatentState,
    rng: np.random.Generator,
) -> int:
    calibration = get_parameter_calibration("beam.proton_count")
    low, high = scaled_calibration_bounds(calibration, float(beam.proton_count))
    centered_draw = sample_lognormal_around_center(float(beam.proton_count), low, high, rng)
    latent_modifier = _bounded_geometric_mean(
        [latent_state.beam_quality, latent_state.system_stability, latent_state.timing_precision],
        lower=0.70,
        upper=1.35,
    )
    jitter = float(
        rng.normal(
            0.0,
            beam.beam_jitter_sigma * (0.85 + (0.15 * latent_state.shock_pressure)),
        )
    )
    realized = centered_draw * latent_modifier * (1.0 + jitter)
    return max(int(round(realized)), 1)
