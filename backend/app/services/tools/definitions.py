"""LLM'nin tool calling modunda çağırabileceği salt okunur araçların merkezi kayıt defteri
(allowlist). Hiçbir araç veritabanına yazmaz, SQL çalıştırmaz veya dosya sistemine erişmez —
yalnızca `app/services/data_providers/` katmanındaki soyut sağlayıcıları çağırır."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import AnomalyType
from app.schemas.json_schema_utils import strict_json_schema
from app.services.data_providers import ProviderBundle
from app.services.synthetic import world
from app.services.tools import schemas as s
from app.services.tools.errors import ToolError, ToolErrorCode

T = TypeVar("T", bound=BaseModel)


def _resolve(fn: Callable[[Session, object], object], db: Session, value: object) -> object:
    try:
        return fn(db, value)
    except world.WorldLookupError as exc:
        raise ToolError(ToolErrorCode.TOOL_VALIDATION_ERROR, str(exc)) from exc


def _check_max_range(args: s._DateRangeArgs) -> None:
    max_days = get_settings().llm_max_date_range_days
    days = (args.end_date - args.start_date).days + 1
    if days > max_days:
        raise ToolError(
            ToolErrorCode.TOOL_VALIDATION_ERROR,
            f"Tarih aralığı {days} gün — izin verilen azami {max_days} günü aşıyor.",
        )


def _resolve_plant_shift_kpi(db: Session, plant_id: str, shift: str | None, kpi: str | None) -> tuple:
    plant = _resolve(world.resolve_plant, db, plant_id)
    shift_obj = _resolve(world.resolve_shift, db, shift)
    kpi_obj = _resolve(world.resolve_kpi, db, kpi) if kpi is not None else None
    return plant, shift_obj, kpi_obj


def _handle_get_anomaly_details(db: Session, providers: ProviderBundle, args: s.GetAnomalyDetailsArgs) -> dict:
    anomaly = _resolve(world.resolve_anomaly, db, args.anomaly_id)
    return providers.anomaly.get_anomaly_details(anomaly.id)


def _handle_get_kpi_history(db: Session, providers: ProviderBundle, args: s.GetKpiHistoryArgs) -> dict:
    _check_max_range(args)
    plant, shift, kpi = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, args.kpi)
    return providers.kpi.get_kpi_history(
        plant.id, shift.id if shift else None, kpi.id, args.start_date, args.end_date, args.granularity
    )


def _handle_compare_shifts(db: Session, providers: ProviderBundle, args: s.CompareShiftsArgs) -> dict:
    _check_max_range(args)
    plant = _resolve(world.resolve_plant, db, args.plant_id)
    kpi = _resolve(world.resolve_kpi, db, args.kpi)
    return providers.kpi.compare_shifts(plant.id, kpi.id, args.start_date, args.end_date)


def _handle_compare_plants(db: Session, providers: ProviderBundle, args: s.ComparePlantsArgs) -> dict:
    _check_max_range(args)
    factory = _resolve(world.resolve_factory, db, args.factory)
    plant = _resolve(world.resolve_plant, db, args.plant_id)
    if plant.factory_id != factory.id:
        raise ToolError(
            ToolErrorCode.TOOL_VALIDATION_ERROR, f"{plant.name}, {factory.code} fabrikasına ait değil."
        )
    kpi = _resolve(world.resolve_kpi, db, args.kpi)
    return providers.kpi.compare_plants(factory.code, plant.id, kpi.id, args.start_date, args.end_date)


def _handle_get_related_kpis(db: Session, providers: ProviderBundle, args: s.GetRelatedKpisArgs) -> dict:
    _check_max_range(args)
    plant, shift, kpi = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, args.primary_kpi)
    return providers.kpi.get_related_kpis(plant.id, shift.id if shift else None, kpi.id, args.start_date, args.end_date)


def _handle_get_downtime_breakdown(db: Session, providers: ProviderBundle, args: s.GetDowntimeBreakdownArgs) -> dict:
    _check_max_range(args)
    plant, shift, _ = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, None)
    return providers.downtime.get_downtime_breakdown(plant.id, shift.id if shift else None, args.start_date, args.end_date)


def _handle_get_maintenance_signals(db: Session, providers: ProviderBundle, args: s.GetMaintenanceSignalsArgs) -> dict:
    _check_max_range(args)
    plant = _resolve(world.resolve_plant, db, args.plant_id)
    return providers.maintenance.get_maintenance_signals(plant.id, args.start_date, args.end_date)


def _handle_get_product_mix(db: Session, providers: ProviderBundle, args: s.GetProductMixArgs) -> dict:
    _check_max_range(args)
    plant, shift, _ = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, None)
    return providers.product.get_product_mix(plant.id, shift.id if shift else None, args.start_date, args.end_date)


def _handle_get_changeover_records(db: Session, providers: ProviderBundle, args: s.GetChangeoverRecordsArgs) -> dict:
    _check_max_range(args)
    plant, shift, _ = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, None)
    return providers.product.get_changeover_records(plant.id, shift.id if shift else None, args.start_date, args.end_date)


def _handle_get_shift_notes(db: Session, providers: ProviderBundle, args: s.GetShiftNotesArgs) -> dict:
    _check_max_range(args)
    plant, shift, _ = _resolve_plant_shift_kpi(db, args.plant_id, args.shift, None)
    return providers.shift.get_shift_notes(plant.id, shift.id if shift else None, args.start_date, args.end_date)


def _handle_find_similar_anomalies(db: Session, providers: ProviderBundle, args: s.FindSimilarAnomaliesArgs) -> dict:
    anomaly = _resolve(world.resolve_anomaly, db, args.anomaly_id)
    kpi = _resolve(world.resolve_kpi, db, args.kpi) if args.kpi else None
    factory = _resolve(world.resolve_factory, db, args.factory) if args.factory else None
    plant = _resolve(world.resolve_plant, db, args.plant_id) if args.plant_id else None
    anomaly_type = None
    if args.anomaly_type:
        try:
            anomaly_type = AnomalyType(args.anomaly_type).value
        except ValueError as exc:
            valid = ", ".join(t.value for t in AnomalyType)
            raise ToolError(
                ToolErrorCode.TOOL_VALIDATION_ERROR, f"Geçersiz tespit türü: {args.anomaly_type!r} (geçerli: {valid})"
            ) from exc
    return providers.historical.find_similar_anomalies(
        anomaly.id, kpi.id if kpi else None, anomaly_type, factory.code if factory else None,
        plant.id if plant else None, args.limit,
    )


@dataclass
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[Session, ProviderBundle, BaseModel], dict]
    read_only: bool = True


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_anomaly_details": ToolDefinition(
        "get_anomaly_details",
        "Bir tespitin tüm temel bilgilerini döndürür (başlık, tesis, vardiya, KPI, sapma, ML güven skoru, veri kalitesi).",
        s.GetAnomalyDetailsArgs, _handle_get_anomaly_details,
    ),
    "get_kpi_history": ToolDefinition(
        "get_kpi_history",
        "Belirli bir tesis/vardiya/KPI için tarih aralığındaki günlük, vardiyalık veya haftalık KPI geçmişini döndürür.",
        s.GetKpiHistoryArgs, _handle_get_kpi_history,
    ),
    "compare_shifts": ToolDefinition(
        "compare_shifts",
        "Bir tesiste bir KPI için 1. ve 2. vardiya ortalamalarını, tesis ortalamasını ve en iyi/en kötü vardiyayı karşılaştırır.",
        s.CompareShiftsArgs, _handle_compare_shifts,
    ),
    "compare_plants": ToolDefinition(
        "compare_plants",
        "Bir tesisi, aynı fabrikadaki (K1/K2) benzer tesislerle bir KPI üzerinden karşılaştırır ve sıralamasını verir.",
        s.ComparePlantsArgs, _handle_compare_plants,
    ),
    "get_related_kpis": ToolDefinition(
        "get_related_kpis",
        "Ana KPI ile aynı dönemde eş zamanlı değişen ilişkili KPI'ların değerlerini ve değişim yönünü döndürür (nedensellik iddia etmez).",
        s.GetRelatedKpisArgs, _handle_get_related_kpis,
    ),
    "get_downtime_breakdown": ToolDefinition(
        "get_downtime_breakdown",
        "Bir tesis/vardiya için duruş sürelerini kategoriye göre (teknik, imalat, ürün değişimi, malzeme/kalite bekleme, personel, diğer) kırılımlar.",
        s.GetDowntimeBreakdownArgs, _handle_get_downtime_breakdown,
    ),
    "get_maintenance_signals": ToolDefinition(
        "get_maintenance_signals",
        "Bir tesis için arıza kayıtlarını, tekrar eden arıza kodlarını, açık bakım taleplerini ve geciken planlı bakımları döndürür.",
        s.GetMaintenanceSignalsArgs, _handle_get_maintenance_signals,
    ),
    "get_product_mix": ToolDefinition(
        "get_product_mix",
        "Bir tesis/vardiyada üretilen ürün gruplarının payını, hedef/gerçekleşen çevrim sürelerini ve karmaşıklık sınıfını döndürür.",
        s.GetProductMixArgs, _handle_get_product_mix,
    ),
    "get_changeover_records": ToolDefinition(
        "get_changeover_records",
        "Bir tesis/vardiyadaki ürün değişim (changeover) olaylarını, hedef/gerçekleşen süreleriyle listeler.",
        s.GetChangeoverRecordsArgs, _handle_get_changeover_records,
    ),
    "get_shift_notes": ToolDefinition(
        "get_shift_notes",
        "Bir tesis/vardiya için devir-teslim notlarını (personel eksikliği, ekipman arızası, ham madde gecikmesi vb.) döndürür.",
        s.GetShiftNotesArgs, _handle_get_shift_notes,
    ),
    "find_similar_anomalies": ToolDefinition(
        "find_similar_anomalies",
        "KPI, tespit türü, fabrika ve tesise göre benzer geçmiş tespitleri, varsa doğrulanmış kök nedenlerini ve uygulanan aksiyonların sonucunu döndürür.",
        s.FindSimilarAnomaliesArgs, _handle_find_similar_anomalies,
    ),
}


def get_tool(name: str) -> ToolDefinition | None:
    return TOOL_REGISTRY.get(name)


def parse_tool_arguments(tool: ToolDefinition, raw_arguments: dict) -> BaseModel:
    try:
        return tool.args_model.model_validate(raw_arguments)
    except ValidationError as exc:
        raise ToolError(ToolErrorCode.TOOL_VALIDATION_ERROR, f"Geçersiz parametre: {exc}") from exc


def list_tool_specs() -> list[dict]:
    """LLM'e (OpenAI `tools` parametresi biçiminde) sunulacak araç tanımları. Yalnızca
    TOOL_REGISTRY'deki allowlist'teki araçlar sunulur — model asla serbest biçimli bir
    araç adı üretemez."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": strict_json_schema(tool.args_model),
                "strict": True,
            },
        }
        for tool in TOOL_REGISTRY.values()
    ]
